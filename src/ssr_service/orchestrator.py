"""Simulation orchestrator bringing together retrieval, elicitation, and SSR."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import get_settings
from .llm.base import LLMProvider, LLMResponse
from .llm.factory import get_provider
from .models import (
    ConceptInput,
    LikertDistribution,
    PersonaQuestionResult,
    PersonaResult,
    PersonaSpec,
    QuestionAggregate,
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


async def generate_batch(
    provider: LLMProvider,
    persona: PersonaSpec,
    prompt_block: str,
    question: str,
    n: int,
    concurrency: int = 32,
    temperature: Optional[float] = None,
) -> List[LLMResponse]:
    semaphore = asyncio.Semaphore(concurrency)
    results: List[LLMResponse] = []

    async def run_single(idx: int) -> None:
        async with semaphore:
            try:
                res = await provider.generate_rationale(
                    persona=persona,
                    prompt_block=prompt_block,
                    question=question,
                    seed=idx,
                    temperature=temperature,
                )
                results.append(res)
            except Exception as err:  # noqa: BLE001
                # One retry in case of transient API issues
                try:
                    res = await provider.generate_rationale(
                        persona=persona,
                        prompt_block=prompt_block,
                        question=question,
                        seed=idx,
                        temperature=temperature,
                    )
                    results.append(res)
                except Exception as inner_err:  # noqa: BLE001
                    raise RuntimeError(
                        "Failed to elicit rationale for persona "
                        f"{persona.name} with {provider.provider_name}: {inner_err}"
                    ) from err

    await asyncio.gather(*(run_single(i) for i in range(n)))
    return results


async def _simulate_persona(
    persona: PersonaSpec,
    artifact: ConceptArtifact,
    question: str,
    question_id: str,
    rater: SemanticSimilarityRater,
    providers: List[LLMProvider],
    draws: int,
    options: SimulationOptions,
) -> Tuple[PersonaQuestionResult, np.ndarray]:
    settings = get_settings()
    
    # Distribute draws across providers
    # Simple strategy: split evenly, or just use the first one if only one
    # If multiple providers, we might want to run 'draws' for EACH provider, or split 'draws' among them.
    # The prompt implies "create queries against multiple LLMs... and capture the responses".
    # Let's assume we want 'draws' responses TOTAL, split across providers.
    
    if not providers:
        raise ValueError("No LLM providers configured")

    draws_per_provider = draws // len(providers)
    remainder = draws % len(providers)
    
    all_results: List[LLMResponse] = []
    
    prompt_block = artifact.as_prompt_block()
    if options.additional_instructions:
        prompt_block += f"\n\nAdditional Instructions:\n{options.additional_instructions}"

    tasks = []
    for i, provider in enumerate(providers):
        count = draws_per_provider + (1 if i < remainder else 0)
        if count > 0:
            tasks.append(
                generate_batch(
                    provider=provider,
                    persona=persona,
                    prompt_block=prompt_block,
                    question=question,
                    n=count,
                    concurrency=min(settings.max_concurrency, 64),
                    temperature=options.temperature,
                )
            )
    
    provider_results_list = await asyncio.gather(*tasks)
    for res_list in provider_results_list:
        all_results.extend(res_list)

    cleaned = [_clean_rationale(res.rationale) for res in all_results]
    pmfs = np.vstack([rater.score_text(text) for text in cleaned])
    persona_pmf = pmfs.mean(axis=0)
    distribution = _make_distribution(persona_pmf, rater.ratings(), sample_n=draws)
    themes = _top_themes(cleaned)

    return (
        PersonaQuestionResult(
            question_id=question_id,
            question=question,
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
            
    # Initialize providers
    provider_names = options.providers or ["openai"]
    providers = [get_provider(name, model_override=options.model) for name in provider_names]

    artifact = await ingest_concept(concept_input)
    anchor_file = request.options.anchor_bank or "purchase_intent_en.yml"
    rater = load_rater(anchor_file)

    intent = request.intent or options.intent
    question = (
        intent_question_override
        or options.intent_question
        or _default_question(intent)
    )

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
    raw_questions = [q.strip() for q in request.questions if q.strip()]
    question_texts = [question] + raw_questions if raw_questions else [question]
    question_ids = [f"q{i + 1}" for i in range(len(question_texts))]

    ratings = rater.ratings()
    weight_vector = np.array([p.weight for p in personas], dtype=float)
    if weight_vector.sum() == 0:
        weight_vector = np.ones(len(personas)) / len(personas)
    else:
        weight_vector = weight_vector / weight_vector.sum()

    persona_question_results: List[List[PersonaQuestionResult]] = [
        [] for _ in personas
    ]
    question_aggregates: List[QuestionAggregate] = []
    question_ci_bounds: List[Tuple[float, float]] = []

    rating_vector = np.array(ratings)

    for qid, qtext in zip(question_ids, question_texts):
        persona_tasks = [
            _simulate_persona(persona, artifact, qtext, qid, rater, providers, draws, options)
            for persona, draws in zip(personas, draw_counts)
        ]

        gathered = await asyncio.gather(*persona_tasks)
        persona_pmfs: List[np.ndarray] = []

        for idx, (result, pmfs) in enumerate(gathered):
            persona_question_results[idx].append(result)
            persona_pmfs.append(pmfs)

        aggregate_pmf = np.zeros(len(ratings), dtype=float)
        aggregate_samples = 0
        all_means = []
        for weight, pmfs, draws in zip(
            weight_vector, persona_pmfs, draw_counts
        ):
            aggregate_pmf += weight * pmfs.mean(axis=0)
            aggregate_samples += draws
            means = pmfs @ rating_vector
            all_means.append(means)

        aggregate_dist = _make_distribution(aggregate_pmf, ratings, aggregate_samples)
        question_aggregates.append(
            QuestionAggregate(question_id=qid, question=qtext, aggregate=aggregate_dist)
        )

        mean_vals = np.concatenate(all_means) if all_means else np.array([])
        ci_lower, ci_upper = _bootstrap_ci(mean_vals)
        question_ci_bounds.append((ci_lower, ci_upper))

    persona_results: List[PersonaResult] = []
    for persona, question_results in zip(personas, persona_question_results):
        first_result = question_results[0]
        persona_results.append(
            PersonaResult(
                persona=persona,
                distribution=first_result.distribution,
                rationales=first_result.rationales,
                themes=first_result.themes,
                question_results=question_results,
            )
        )

    first_question_dist = question_aggregates[0].aggregate
    ci_lower, ci_upper = question_ci_bounds[0]

    metadata: Dict[str, str] = {
        "question": question_texts[0],
        "anchor_bank": anchor_file,
        "intent": intent,
        "description_length": str(len(artifact.description)),
        "draw_allocation": ",".join(str(d) for d in draw_counts),
        "ci_mean_lower": f"{ci_lower:.3f}",
        "ci_mean_upper": f"{ci_upper:.3f}",
        "persona_summary": _summarize_personas(persona_results),
        "persona_total": str(len(personas)),
        "question_count": str(len(question_texts)),
        "providers": ",".join(p.provider_name for p in providers),
    }

    for idx, qtext in enumerate(question_texts, start=1):
        metadata[f"question_{idx}"] = qtext
        lower, upper = question_ci_bounds[idx - 1]
        metadata[f"ci_mean_lower_q{idx}"] = f"{lower:.3f}"
        metadata[f"ci_mean_upper_q{idx}"] = f"{upper:.3f}"

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
        aggregate=first_question_dist,
        personas=persona_results,
        metadata=metadata,
        questions=question_aggregates,
    )


__all__ = ["run_simulation"]
