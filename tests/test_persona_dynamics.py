"""Tests for dynamic persona filtering and generation."""

from __future__ import annotations

import numpy as np
import pytest

from ssr_service.config import AppSettings
from ssr_service.models import (
    ConceptInput,
    LikertDistribution,
    PersonaFilter,
    PersonaGenerationTask,
    PersonaInjection,
    PersonaQuestionResult,
    PersonaSpec,
    PopulationSpec,
    RakingConfig,
    SimulationOptions,
    SimulationRequest,
)
from ssr_service.orchestrator import run_simulation
from ssr_service.persona_generation import synthesize_personas
from ssr_service.personas import (
    combine_persona_buckets,
    filter_personas,
    get_persona_library,
)
from ssr_service.population import rake_personas


def test_filter_personas_by_age_and_keyword():
    library = get_persona_library("src/ssr_service/data/personas")
    persona_filter = PersonaFilter(
        group="us_toothpaste_buyers",
        include={"age": ["25-44"]},
        keywords=["family"],
    )
    personas = filter_personas(library, persona_filter)
    assert personas, "Expected at least one persona matching the filter"
    assert all(persona.age == "25-44" for persona in personas)
    assert any("family" in persona.describe().lower() for persona in personas)


def test_combine_persona_buckets_respects_weight_share():
    buckets = [
        ([PersonaSpec(name="Primary", weight=0.6)], 0.6),
        ([PersonaSpec(name="Secondary", weight=1.0)], None),
    ]
    combined = combine_persona_buckets(buckets)
    weights = {persona.name: persona.weight for persona in combined}
    assert pytest.approx(weights["Primary"], rel=1e-6) == 0.6
    assert pytest.approx(weights["Secondary"], rel=1e-6) == 0.4
    assert pytest.approx(sum(weights.values()), rel=1e-6) == 1.0


@pytest.mark.asyncio
async def test_synthesize_personas_heuristic():
    settings = AppSettings()
    task = PersonaGenerationTask(
        prompt="Eco-conscious parents in urban areas",
        count=2,
    )
    personas = await synthesize_personas(task, settings)
    assert len(personas) == 2
    assert all(isinstance(persona, PersonaSpec) for persona in personas)
    assert all(persona.descriptors for persona in personas)


@pytest.mark.asyncio
async def test_synthesize_personas_openai_fallback_without_credentials():
    settings = AppSettings()
    task = PersonaGenerationTask(
        prompt="Luxury travelers seeking bespoke experiences",
        count=1,
        strategy="openai",
    )
    personas = await synthesize_personas(task, settings)
    assert personas, "Fallback generator should yield personas when OpenAI is unavailable"


@pytest.mark.asyncio
async def test_run_simulation_with_dynamic_personas(monkeypatch):
    class DummyProvider:
        provider_name = "dummy"
        
        async def generate_rationale(self, persona, prompt_block, question, seed=None, temperature=None):
            from ssr_service.llm.base import LLMResponse
            return LLMResponse(
                rationale="sample rationale",
                provider="dummy",
                model="dummy-model"
            )

    async def fake_ingest_concept(concept: ConceptInput):
        class Artifact:
            description = concept.text or ""

            @staticmethod
            def as_prompt_block() -> str:
                return "concept block"

        return Artifact()

    def fake_load_rater(anchor_file: str):  # noqa: ARG001
        class Rater:
            @staticmethod
            def ratings() -> list[int]:
                return [1, 2, 3, 4, 5]
            
            @staticmethod
            def score_text(text: str) -> np.ndarray:
                return np.array([0.1, 0.2, 0.3, 0.25, 0.15])

        return Rater()

    monkeypatch.setattr("ssr_service.orchestrator.get_provider", lambda name, model_override=None: DummyProvider())
    monkeypatch.setattr("ssr_service.orchestrator.ingest_concept", fake_ingest_concept)
    monkeypatch.setattr("ssr_service.orchestrator.load_rater", fake_load_rater)

    request = SimulationRequest(
        concept=ConceptInput(text="Concept for dynamic personas"),
        persona_group="us_toothpaste_buyers",
        persona_filters=[
            PersonaFilter(include={"age": ["25-44"]}, weight_share=0.5),
        ],
        persona_injections=[
            PersonaInjection(
                persona=PersonaSpec(
                    name="Custom Segment",
                    descriptors=["custom"],
                    weight=1.0,
                ),
                weight_share=0.2,
            )
        ],
        persona_generations=[
            PersonaGenerationTask(
                prompt="Eco-friendly professionals",
                count=1,
                weight_share=0.3,
            )
        ],
        options=SimulationOptions(n=25, stratified=True, total_n=100),
    )

    response = await run_simulation(request)

    assert response.aggregate.sample_n == 100
    persona_names = {result.persona.name for result in response.personas}
    assert "Custom Segment" in persona_names
    assert any("eco" in name.lower() or "generated" in name for name in persona_names)
    assert response.metadata.get("persona_total")
    assert response.metadata.get("question_count") == "1"
    assert len(response.questions) == 1


def test_rake_personas_lenient_handles_missing_categories():
    personas = [
        PersonaSpec(name="A", age="18-24", weight=0.4),
        PersonaSpec(name="B", age="25-44", weight=0.6),
    ]
    marginals = {"age": {"18-24": 0.2, "25-44": 0.8, "45-64": 0.0}}
    config = RakingConfig(enabled=True, mode="lenient", iterations=10)

    adjusted = rake_personas(personas, marginals, config)
    weights = {p.name: p.weight for p in adjusted}
    assert pytest.approx(weights["A"], rel=1e-6) == pytest.approx(0.2, rel=1e-6)
    assert pytest.approx(weights["B"], rel=1e-6) == pytest.approx(0.8, rel=1e-6)


def test_rake_personas_strict_raises_on_missing_cells():
    personas = [
        PersonaSpec(name="A", age="18-24", weight=1.0),
    ]
    marginals = {"age": {"18-24": 0.5, "25-44": 0.5}}
    config = RakingConfig(enabled=True, mode="strict", iterations=5)

    with pytest.raises(ValueError):
        rake_personas(personas, marginals, config)


@pytest.mark.asyncio
async def test_run_simulation_with_population_spec(monkeypatch):
    class DummyProvider:
        provider_name = "dummy"
        
        async def generate_rationale(self, persona, prompt_block, question, seed=None, temperature=None):
            from ssr_service.llm.base import LLMResponse
            return LLMResponse(
                rationale="sample rationale",
                provider="dummy",
                model="dummy-model"
            )

    async def fake_ingest_concept(concept: ConceptInput):
        class Artifact:
            description = concept.text or ""

            @staticmethod
            def as_prompt_block() -> str:
                return "concept block"

        return Artifact()

    def fake_load_rater(anchor_file: str):  # noqa: ARG001
        class Rater:
            @staticmethod
            def ratings() -> list[int]:
                return [1, 2, 3, 4, 5]
            
            @staticmethod
            def score_text(text: str) -> np.ndarray:
                return np.array([0.1, 0.2, 0.3, 0.25, 0.15])

        return Rater()

    monkeypatch.setattr("ssr_service.orchestrator.get_provider", lambda name, model_override=None: DummyProvider())
    monkeypatch.setattr("ssr_service.orchestrator.ingest_concept", fake_ingest_concept)
    monkeypatch.setattr("ssr_service.orchestrator.load_rater", fake_load_rater)

    population_spec = PopulationSpec(
        base_group="us_toothpaste_buyers",
        filters=[PersonaFilter(include={"age": ["25-44"]}, weight_share=0.4)],
        generations=[
            PersonaGenerationTask(
                prompt="Wellness enthusiasts",
                count=1,
                weight_share=0.2,
            )
        ],
        marginals={"age": {"25-44": 0.5, "45-64": 0.5}},
        raking=RakingConfig(enabled=True, mode="lenient", iterations=10),
    )

    request = SimulationRequest(
        concept=ConceptInput(text="Population spec test"),
        population_spec=population_spec,
        options=SimulationOptions(n=10, stratified=True, total_n=40),
    )

    response = await run_simulation(request)

    assert response.aggregate.sample_n == 40
    ages = [res.persona.age for res in response.personas if res.persona.age]
    assert ages, "Expected personas with age attributes"
    assert "population_spec" in response.metadata
    assert response.metadata.get("question_count") == "1"
    assert response.questions
