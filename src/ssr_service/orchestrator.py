"""Simulation orchestrator bringing together retrieval, elicitation, and SSR."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import AppSettings, get_settings
from .llm.base import LLMProvider, LLMResponse
from .llm.factory import get_provider
from .models import (
    ConceptInput,
    LikertDistribution,
    PanelAllocation,
    PanelPreviewResponse,
    PersonaQuestionResult,
    PersonaResult,
    PersonaSpec,
    QuestionAggregate,
    QuestionSpec,
    RespondentAnswer,
    RespondentResult,
    SimulationOptions,
    SimulationRequest,
    SimulationResponse,
    coerce_http_url,
)
from .panel_context import apply_panel_context
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

DEFAULT_ANCHOR_BANK_BY_INTENT: Dict[str, str] = {
    "purchase_intent": "purchase_intent_en.yml",
    "relevance": "purchase_intent_en.yml",
    "trust": "trust_en.yml",
    "clarity": "clarity_en.yml",
    "value_for_money": "value_for_money_en.yml",
    "differentiation": "differentiation_en.yml",
}


def _default_question(intent: str) -> str:
    lookup = {
        "purchase_intent": "How likely would you be to purchase this product?",
        "relevance": "How relevant is this concept to your needs?",
        "trust": "How much do you trust this product or brand to deliver what it promises?",
        "clarity": "How clear is what this product is and what it does?",
        "value_for_money": "How good is the value for the money based on what you see here?",
        "differentiation": "How different does this feel compared to alternatives you know?",
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
    seed_offset: int = 0,
    concurrency: int = 32,
    temperature: Optional[float] = None,
) -> List[LLMResponse]:
    semaphore = asyncio.Semaphore(concurrency)
    results: List[Optional[LLMResponse]] = [None] * n

    async def run_single(idx: int) -> None:
        async with semaphore:
            try:
                res = await provider.generate_rationale(
                    persona=persona,
                    prompt_block=prompt_block,
                    question=question,
                    seed=seed_offset + idx,
                    temperature=temperature,
                )
                results[idx] = res
            except Exception as err:  # noqa: BLE001
                # One retry in case of transient API issues
                try:
                    res = await provider.generate_rationale(
                        persona=persona,
                        prompt_block=prompt_block,
                        question=question,
                        seed=seed_offset + idx,
                        temperature=temperature,
                    )
                    results[idx] = res
                except Exception as inner_err:  # noqa: BLE001
                    raise RuntimeError(
                        "Failed to elicit rationale for persona "
                        f"{persona.name} with {provider.provider_name}: {inner_err}"
                    ) from err

    await asyncio.gather(*(run_single(i) for i in range(n)))
    ordered = [res for res in results if res is not None]
    if len(ordered) != n:  # pragma: no cover - defensive guard
        raise RuntimeError("Rationale batch did not return all responses")
    return ordered


async def _simulate_persona(
    persona: PersonaSpec,
    artifact: ConceptArtifact,
    question: str,
    question_id: str,
    intent: str,
    anchor_bank: str,
    rater: SemanticSimilarityRater,
    providers: List[LLMProvider],
    draws: int,
    seed_base: int,
    options: SimulationOptions,
) -> Tuple[PersonaQuestionResult, np.ndarray, List[LLMResponse]]:
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
    seed_offset = seed_base
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
                    seed_offset=seed_offset,
                    concurrency=min(settings.max_concurrency, 64),
                    temperature=options.temperature,
                )
            )
            seed_offset += count
    
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
            intent=intent,
            anchor_bank=anchor_bank,
            distribution=distribution,
            rationales=cleaned,
            themes=themes,
        ),
        pmfs,
        all_results,
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


def _default_anchor_bank(intent: str, fallback: str) -> str:
    return DEFAULT_ANCHOR_BANK_BY_INTENT.get(intent, fallback)


def _build_question_specs(
    request: SimulationRequest, options: SimulationOptions
) -> List[QuestionSpec]:
    base_intent = request.intent or options.intent
    base_question = (
        request.intent_question
        or options.intent_question
        or _default_question(base_intent)
    )
    base_anchor = options.anchor_bank or DEFAULT_ANCHOR_BANK_BY_INTENT["purchase_intent"]

    specs: List[QuestionSpec] = []
    for spec in request.questionnaire:
        text = spec.text.strip()
        if not text:
            continue
        specs.append(spec.model_copy(deep=True, update={"text": text}))

    if not specs:
        specs.append(
            QuestionSpec(
                id="q1",
                text=base_question.strip(),
                intent=base_intent,
                anchor_bank=_default_anchor_bank(base_intent, base_anchor),
            )
        )

    default_intent = specs[0].intent or base_intent
    default_anchor = specs[0].anchor_bank or _default_anchor_bank(default_intent, base_anchor)

    raw_questions = [q.strip() for q in request.questions if q and q.strip()]
    for q in raw_questions:
        specs.append(QuestionSpec(text=q, intent=default_intent, anchor_bank=default_anchor))

    for idx, spec in enumerate(specs, start=1):
        if not spec.id:
            spec.id = f"q{idx}"
        if not spec.intent:
            spec.intent = default_intent
        if not spec.anchor_bank:
            spec.anchor_bank = _default_anchor_bank(spec.intent, default_anchor)

    return specs


async def _assemble_panel(
    *,
    request: SimulationRequest,
    persona_group: Optional[str],
    settings: AppSettings,
    options: SimulationOptions,
) -> tuple[List[PersonaSpec], List[int], Optional[str], Dict[str, str], bool]:
    library = get_persona_library(settings.persona_library_path)
    persona_group_source = None
    persona_buckets: List[Tuple[List[PersonaSpec], Optional[float]]] = []
    population_spec = request.population_spec
    population_spec_summary: Dict[str, str] = {}
    panel_context_chunks = 0

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
        spec_buckets = await buckets_from_population_spec(
            population_spec, library, settings
        )
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

    if request.panel_context:
        panel_context_chunks = apply_panel_context(personas, request.panel_context, seed=options.seed)

    draw_counts = _allocate_draws(personas, options)

    metadata: Dict[str, str] = {
        "persona_total": str(len(personas)),
        "total_samples": str(sum(draw_counts)),
        "draw_allocation": ",".join(str(d) for d in draw_counts),
    }
    if request.panel_context and panel_context_chunks > 0:
        metadata["panel_context_chunks"] = str(panel_context_chunks)
        metadata["panel_context_mode"] = request.panel_context.mode
        metadata["panel_context_per_persona"] = str(request.panel_context.chunks_per_persona)
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

    return personas, draw_counts, persona_group_source, metadata, raking_applied


async def preview_panel(request: SimulationRequest) -> PanelPreviewResponse:
    settings = get_settings()
    persona_group = request.persona_group

    if request.sample_id:
        sample = load_sample(request.sample_id)
        persona_group = persona_group or sample.persona_group
        if not request.intent_question and sample.intent_question:
            request = request.model_copy(update={"intent_question": sample.intent_question})

    question_specs = _build_question_specs(request, request.options)
    personas, draw_counts, _, metadata, _ = await _assemble_panel(
        request=request,
        persona_group=persona_group,
        settings=settings,
        options=request.options,
    )

    panel = [
        PanelAllocation(persona=persona, draws=draws)
        for persona, draws in zip(personas, draw_counts)
    ]

    return PanelPreviewResponse(panel=panel, questions=question_specs, metadata=metadata)


async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    settings = get_settings()

    concept_input = request.concept
    persona_group = request.persona_group
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
        if not request.intent_question and sample.intent_question:
            request = request.model_copy(update={"intent_question": sample.intent_question})
            
    # Initialize providers
    provider_names = options.providers or ["openai"]
    providers = [get_provider(name, model_override=options.model) for name in provider_names]

    artifact = await ingest_concept(concept_input)
    question_specs = _build_question_specs(request, options)
    personas, draw_counts, persona_group_source, panel_metadata, raking_applied = await _assemble_panel(
        request=request,
        persona_group=persona_group,
        settings=settings,
        options=options,
    )
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

    respondent_tables: List[List[RespondentResult]] = []
    if options.include_respondents:
        for persona_idx, draws in enumerate(draw_counts):
            respondent_tables.append(
                [
                    RespondentResult(
                        respondent_id=f"p{persona_idx + 1}_r{idx + 1}",
                    )
                    for idx in range(draws)
                ]
            )

    rater_cache: Dict[str, SemanticSimilarityRater] = {}

    for spec in question_specs:
        qid = spec.id or "q1"
        qtext = spec.text
        intent = spec.intent or options.intent
        anchor_bank = spec.anchor_bank or (options.anchor_bank or DEFAULT_ANCHOR_BANK_BY_INTENT["purchase_intent"])
        rater = rater_cache.get(anchor_bank)
        if rater is None:
            rater = load_rater(anchor_bank)
            rater_cache[anchor_bank] = rater
        ratings = rater.ratings()
        rating_vector = np.array(ratings)

        persona_tasks = [
            _simulate_persona(
                persona,
                artifact,
                qtext,
                qid,
                intent,
                anchor_bank,
                rater,
                providers,
                draws,
                options.seed + persona_idx * 1_000_000,
                options,
            )
            for persona_idx, (persona, draws) in enumerate(zip(personas, draw_counts))
        ]

        gathered = await asyncio.gather(*persona_tasks)
        persona_pmfs: List[np.ndarray] = []

        for idx, (result, pmfs, responses) in enumerate(gathered):
            persona_question_results[idx].append(result)
            persona_pmfs.append(pmfs)
            if options.include_respondents:
                for resp_idx, response in enumerate(responses):
                    if idx >= len(respondent_tables) or resp_idx >= len(
                        respondent_tables[idx]
                    ):
                        continue
                    respondent_tables[idx][resp_idx].answers.append(
                        RespondentAnswer(
                            question_id=qid,
                            intent=intent,
                            anchor_bank=anchor_bank,
                            provider=response.provider,
                            model=response.model,
                            rationale=result.rationales[resp_idx],
                            score_mean=float(pmfs[resp_idx] @ rating_vector),
                        )
                    )

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
            QuestionAggregate(
                question_id=qid,
                question=qtext,
                intent=intent,
                anchor_bank=anchor_bank,
                aggregate=aggregate_dist,
            )
        )

        mean_vals = np.concatenate(all_means) if all_means else np.array([])
        ci_lower, ci_upper = _bootstrap_ci(mean_vals)
        question_ci_bounds.append((ci_lower, ci_upper))

    persona_results: List[PersonaResult] = []
    for idx, (persona, question_results) in enumerate(
        zip(personas, persona_question_results)
    ):
        first_result = question_results[0]
        persona_results.append(
            PersonaResult(
                persona=persona,
                distribution=first_result.distribution,
                rationales=first_result.rationales,
                themes=first_result.themes,
                question_results=question_results,
                respondents=respondent_tables[idx] if options.include_respondents else [],
            )
        )

    first_question_dist = question_aggregates[0].aggregate
    ci_lower, ci_upper = question_ci_bounds[0]

    first_spec = question_specs[0]
    metadata: Dict[str, str] = {
        "question": first_spec.text,
        "anchor_bank": first_spec.anchor_bank or "",
        "intent": first_spec.intent or "",
        "description_length": str(len(artifact.description)),
        "draw_allocation": ",".join(str(d) for d in draw_counts),
        "ci_mean_lower": f"{ci_lower:.3f}",
        "ci_mean_upper": f"{ci_upper:.3f}",
        "persona_summary": _summarize_personas(persona_results),
        "persona_total": str(len(personas)),
        "question_count": str(len(question_specs)),
        "providers": ",".join(p.provider_name for p in providers),
    }
    metadata.update(panel_metadata)

    for idx, spec in enumerate(question_specs, start=1):
        metadata[f"question_{idx}"] = spec.text
        metadata[f"intent_q{idx}"] = spec.intent or ""
        metadata[f"anchor_bank_q{idx}"] = spec.anchor_bank or ""
        lower, upper = question_ci_bounds[idx - 1]
        metadata[f"ci_mean_lower_q{idx}"] = f"{lower:.3f}"
        metadata[f"ci_mean_upper_q{idx}"] = f"{upper:.3f}"

    if request.sample_id:
        metadata["sample_id"] = request.sample_id
    if raking_applied and request.population_spec:
        metadata.setdefault("population_spec_raking", request.population_spec.raking.mode)

    return SimulationResponse(
        aggregate=first_question_dist,
        personas=persona_results,
        metadata=metadata,
        questions=question_aggregates,
    )


__all__ = ["preview_panel", "run_simulation"]
