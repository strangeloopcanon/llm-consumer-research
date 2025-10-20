"""Helpers that expose a simplified entry point for running simulations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

from .models import (
    ConceptInput,
    PersonaFilter,
    PersonaGenerationTask,
    PersonaInjection,
    PopulationSpec,
    SimulationOptions,
    SimulationRequest,
    SimulationResponse,
    coerce_http_url,
)
from .orchestrator import run_simulation


def build_simple_request(
    *,
    concept_text: str,
    title: Optional[str] = None,
    price: Optional[str] = None,
    concept_url: Optional[str] = None,
    persona_group: Optional[str] = None,
    persona_csv_path: Optional[Path] = None,
    persona_csv_text: Optional[str] = None,
    persona_filters: Optional[List[PersonaFilter]] = None,
    persona_generations: Optional[List[PersonaGenerationTask]] = None,
    persona_injections: Optional[List[PersonaInjection]] = None,
    population_spec: Optional[PopulationSpec] = None,
    samples_per_persona: int = 50,
    total_samples: Optional[int] = None,
    stratified: bool = True,
    intent_question: Optional[str] = None,
) -> SimulationRequest:
    """Create a `SimulationRequest` with sensible defaults for quick runs."""
    if not concept_text and not concept_url:
        raise ValueError("Provide either concept_text or concept_url.")

    csv_data: Optional[str] = persona_csv_text
    if persona_csv_path is not None:
        csv_data = Path(persona_csv_path).read_text(encoding="utf-8")

    concept = ConceptInput(
        title=title or None,
        text=concept_text or None,
        price=price or None,
        url=coerce_http_url(concept_url),
    )

    options = SimulationOptions(
        n=max(samples_per_persona, 1),
        total_n=total_samples,
        stratified=stratified,
    )

    return SimulationRequest(
        concept=concept,
        persona_group=persona_group,
        persona_csv=csv_data,
        persona_filters=list(persona_filters or []),
        persona_generations=list(persona_generations or []),
        persona_injections=list(persona_injections or []),
        population_spec=population_spec,
        intent_question=intent_question,
        options=options,
    )


def run_simple_simulation(
    *,
    concept_text: str,
    title: Optional[str] = None,
    price: Optional[str] = None,
    concept_url: Optional[str] = None,
    persona_group: Optional[str] = None,
    persona_csv_path: Optional[Path] = None,
    persona_csv_text: Optional[str] = None,
    persona_filters: Optional[List[PersonaFilter]] = None,
    persona_generations: Optional[List[PersonaGenerationTask]] = None,
    persona_injections: Optional[List[PersonaInjection]] = None,
    population_spec: Optional[PopulationSpec] = None,
    samples_per_persona: int = 50,
    total_samples: Optional[int] = None,
    stratified: bool = True,
    intent_question: Optional[str] = None,
) -> SimulationResponse:
    """Run a simulation end-to-end using the simplified configuration."""
    request = build_simple_request(
        concept_text=concept_text,
        title=title,
        price=price,
        concept_url=concept_url,
        persona_group=persona_group,
        persona_csv_path=persona_csv_path,
        persona_csv_text=persona_csv_text,
        persona_filters=persona_filters,
        persona_generations=persona_generations,
        persona_injections=persona_injections,
        population_spec=population_spec,
        samples_per_persona=samples_per_persona,
        total_samples=total_samples,
        stratified=stratified,
        intent_question=intent_question,
    )
    return asyncio.run(run_simulation(request))


__all__ = ["build_simple_request", "run_simple_simulation"]
