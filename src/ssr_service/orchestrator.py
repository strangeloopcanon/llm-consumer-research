"""Simulation orchestrator bringing together retrieval, elicitation, and SSR."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import get_settings
from .elicitation import ElicitationClient, generate_batch
from .models import (
    ConceptInput,
    LikertDistribution,
    PersonaResult,
    PersonaSpec,
    SimulationOptions,
    SimulationRequest,
    SimulationResponse,
    coerce_http_url,
)
from .persona_generation import synthesize_personas
from .personas import (
    combine_persona_buckets,
    filter_personas,
    get_persona_library,
    personas_from_csv,
)
from .population import buckets_from_population_spec, rake_personas
from .retrieval import ConceptArtifact, ingest_concept
from .sample_data import load_sample
from .ssr import SemanticSimilarityRater, likert_metrics, load_rater


def _default_question(intent: str) -> str:
    lookup = {
        "purchase_intent": "How likely would you be to purchase this product?",
        "relevance": "How relevant is this concept to your needs?",
    }
    return lookup.get(intent, "How do you feel about this offering?")


def _clean_rationale(text: str) -> str:
    return text.replace("\n", " ").strip()


def _top_themes(rationales: List[str], limit: int = 3) -> List[str]:
    tokens = []
    for text in rationales:
        for word in text.lower().split():
            word = word.strip(".,!?()")
            if len(word) <= 3 or not word.isalpha():
                continue
            tokens.append(word)
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def _bootstrap_ci(
    measurements: np.ndarray, samples: int = 200, alpha: float = 0.05
) -> Tuple[float, float]:
    if measurements.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(42)
    stats = []
    for _ in range(samples):
        resample = rng.choice(measurements, size=measurements.size, replace=True)
        stats.append(resample.mean())
    lower = float(np.quantile(stats, alpha / 2))
    upper = float(np.quantile(stats, 1 - alpha / 2))
    return lower, upper


def _make_distribution(
    pmf: np.ndarray, ratings: List[int], sample_n: int
) -> LikertDistribution:
    mean, top2 = likert_metrics(pmf, ratings)
    return LikertDistribution(
        ratings=ratings,
        pmf=pmf.round(6).tolist(),
        mean=mean,
        top2box=top2,
        sample_n=sample_n,
    )


def _persona_highlights(persona: PersonaSpec) -> List[str]:
    highlights: List[str] = []
    if persona.age:
        highlights.append(f"age {persona.age}")
    if persona.gender:
        highlights.append(persona.gender)
    if persona.region:
        highlights.append(persona.region)
    if persona.income:
        highlights.append(f"income {persona.income}")
    if persona.occupation:
        highlights.append(persona.occupation)
    if persona.habits:
        highlights.append("habits: " + ", ".join(persona.habits[:2]))
    if persona.motivations:
        highlights.append("motivations: " + ", ".join(persona.motivations[:2]))
    if persona.preferred_channels:
        highlights.append(
            "channels: " + ", ".join(persona.preferred_channels[:2])
        )
    return highlights[:4]


def _summarize_personas(persona_results: List[PersonaResult]) -> str:
    if not persona_results:
        return ""
    segments = []
    for result in persona_results:
        persona = result.persona
        highlights = _persona_highlights(persona)
        if highlights:
            segments.append(f"{persona.name}: {'; '.join(highlights)}")
        else:
            segments.append(persona.name)
    return " | ".join(segments)


async def _simulate_persona(
    persona: PersonaSpec,
    artifact: ConceptArtifact,
    question: str,
    rater: SemanticSimilarityRater,
    client: ElicitationClient,
    draws: int,
) -> Tuple[PersonaResult, np.ndarray]:
    settings = get_settings()
    results = await generate_batch(
        client=client,
        persona=persona,
        prompt_block=artifact.as_prompt_block(),
        question=question,
        n=draws,
        concurrency=min(settings.max_concurrency, 64),
    )

    cleaned = [_clean_rationale(res.rationale) for res in results]
    pmfs = np.vstack([rater.score_text(text) for text in cleaned])
    persona_pmf = pmfs.mean(axis=0)
    distribution = _make_distribution(persona_pmf, rater.ratings(), sample_n=draws)
    themes = _top_themes(cleaned)

    return (
        PersonaResult(
            persona=persona,
            distribution=distribution,
            rationales=cleaned,
            themes=themes,
        ),
        pmfs,
    )


def _allocate_draws(
    personas: List[PersonaSpec], options: SimulationOptions
) -> List[int]:
    if not personas:
        return []

    if options.total_n:
        total = options.total_n
    elif options.stratified:
        total = options.n
    else:
        return [options.n] * len(personas)

    weights = np.array([p.weight for p in personas], dtype=float)
    if weights.sum() == 0:
        weights = np.ones(len(personas)) / len(personas)
    else:
        weights = weights / weights.sum()

    raw = weights * total
    base = np.floor(raw).astype(int)
    # Ensure at least one sample per persona
    base = np.maximum(base, 1)
    remainder = total - int(base.sum())

    if remainder > 0:
        fractional = raw - np.floor(raw)
        order = np.argsort(-fractional)
        for idx in order[:remainder]:
            base[idx] += 1
    elif remainder < 0:
        # remove from smallest fractional contributions while keeping minimum 1
        fractional = raw - np.floor(raw)
        order = np.argsort(fractional)
        idx = 0
        while remainder < 0 and idx < len(order):
            candidate = order[idx]
            if base[candidate] > 1:
                base[candidate] -= 1
                remainder += 1
            else:
                idx += 1

    return base.tolist()


async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    settings = get_settings()

    concept_input = request.concept
    persona_group = request.persona_group
    intent_question_override = request.intent_question
    options = request.options

    if request.sample_id:
        sample = load_sample(request.sample_id)
        combined_url = coerce_http_url(concept_input.url) or coerce_http_url(
            sample.source
        )
        concept_input = ConceptInput(
            title=concept_input.title or sample.title,
            text=concept_input.text or sample.description,
            price=concept_input.price or sample.price,
            url=combined_url,
        )
        persona_group = persona_group or sample.persona_group
        if not intent_question_override and sample.intent_question:
            intent_question_override = sample.intent_question

    artifact = await ingest_concept(concept_input)
    anchor_file = request.options.anchor_bank or "purchase_intent_en.yml"
    rater = load_rater(anchor_file)

    intent = request.intent or options.intent
    question = (
        intent_question_override
        or options.intent_question
        or _default_question(intent)
    )

    client = ElicitationClient(model_override=options.model)

    library = get_persona_library(settings.persona_library_path)
    persona_group_source = None
    persona_buckets: List[Tuple[List[PersonaSpec], Optional[float]]] = []
    population_spec = request.population_spec
    population_spec_summary: Dict[str, str] = {}

    if request.personas:
        persona_buckets.append(
            ([persona.model_copy(deep=True) for persona in request.personas], None)
        )

    if persona_group:
        group = library.get_group(persona_group)
        persona_group_source = group.source
        persona_buckets.append(
            ([persona.model_copy(deep=True) for persona in group.personas], None)
        )

    if request.persona_csv:
        persona_buckets.append((personas_from_csv(request.persona_csv), None))

    for injection in request.persona_injections:
        persona = injection.persona.model_copy(deep=True)
        persona_buckets.append(([persona], injection.weight_share))

    for persona_filter in request.persona_filters:
        effective_filter = persona_filter.model_copy(deep=True)
        if effective_filter.group is None and persona_group:
            effective_filter.group = persona_group
        filtered = filter_personas(library, effective_filter)
        if not filtered:
            continue
        persona_buckets.append((filtered, persona_filter.weight_share))

    for generation in request.persona_generations:
        generated = await synthesize_personas(generation, settings)
        if not generated:
            continue
        persona_buckets.append((generated, generation.weight_share))

    if population_spec:
        spec_buckets = await buckets_from_population_spec(population_spec, library, settings)
        if spec_buckets:
            persona_buckets.extend(spec_buckets)
        population_spec_summary = {
            "base_group": population_spec.base_group or "",
            "filters": str(len(population_spec.filters)),
            "generations": str(len(population_spec.generations)),
            "injections": str(len(population_spec.injections)),
            "marginals": str(len(population_spec.marginals)),
        }

    if not persona_buckets:
        default_persona = PersonaSpec(
            name="General Consumer", descriptors=["broad audience"], weight=1.0
        )
        persona_buckets.append(([default_persona], None))

    personas = combine_persona_buckets(persona_buckets)
    if not personas:
        raise RuntimeError("No personas available after applying filters and generation.")

    raking_applied = False
    if population_spec and population_spec.raking.enabled:
        personas = rake_personas(personas, population_spec.marginals, population_spec.raking)
        raking_applied = bool(population_spec.marginals)

    draw_counts = _allocate_draws(personas, options)

    persona_tasks = [
        _simulate_persona(persona, artifact, question, rater, client, draws)
        for persona, draws in zip(personas, draw_counts)
    ]

    persona_results: List[PersonaResult] = []
    persona_pmfs: List[np.ndarray] = []

    for result, pmfs in await asyncio.gather(*persona_tasks):
        persona_results.append(result)
        persona_pmfs.append(pmfs)

    ratings = rater.ratings()
    weights = np.array([p.persona.weight for p in persona_results], dtype=float)
    weights = weights / weights.sum()

    aggregate_pmf = np.zeros(len(ratings), dtype=float)
    aggregate_samples = 0
    all_means = []
    for weight, persona_result, pmfs, draws in zip(
        weights, persona_results, persona_pmfs, draw_counts
    ):
        aggregate_pmf += weight * pmfs.mean(axis=0)
        aggregate_samples += draws
        means = pmfs @ np.array(ratings)
        all_means.append(means)

    aggregate_dist = _make_distribution(aggregate_pmf, ratings, aggregate_samples)

    mean_vals = np.concatenate(all_means)
    ci_lower, ci_upper = _bootstrap_ci(mean_vals)

    metadata: Dict[str, str] = {
        "question": question,
        "anchor_bank": anchor_file,
        "intent": intent,
        "description_length": str(len(artifact.description)),
        "draw_allocation": ",".join(str(d) for d in draw_counts),
        "ci_mean_lower": f"{ci_lower:.3f}",
        "ci_mean_upper": f"{ci_upper:.3f}",
        "persona_summary": _summarize_personas(persona_results),
        "persona_total": str(len(personas)),
    }

    if request.sample_id:
        metadata["sample_id"] = request.sample_id
    if persona_group:
        metadata["persona_group"] = persona_group
    if persona_group_source:
        metadata["persona_group_source"] = persona_group_source
    if request.persona_filters:
        metadata["persona_filters"] = str(len(request.persona_filters))
    if request.persona_injections:
        metadata["persona_injections"] = str(len(request.persona_injections))
    if request.persona_generations:
        metadata["persona_generations"] = ";".join(
            task.prompt for task in request.persona_generations
        )
    if population_spec:
        metadata["population_spec"] = ",".join(
            f"{key}={value}" for key, value in population_spec_summary.items() if value
        ) or "true"
        if population_spec.raking.enabled:
            metadata["population_spec_raking"] = population_spec.raking.mode
            if not population_spec.marginals:
                metadata["population_spec_raking"] += " (no marginals)"
            elif raking_applied:
                metadata["population_spec_raking"] += f" ({population_spec.raking.iterations} iters)"

    return SimulationResponse(
        aggregate=aggregate_dist,
        personas=persona_results,
        metadata=metadata,
    )


__all__ = ["run_simulation"]
