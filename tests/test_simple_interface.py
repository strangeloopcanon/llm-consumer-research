"""Tests for the simplified simulation interface."""

from __future__ import annotations

from typing import Any

import pytest

from ssr_service import simple_interface
from ssr_service.models import (
    LikertDistribution,
    PersonaResult,
    PersonaSpec,
    SimulationRequest,
    SimulationResponse,
)


def test_build_simple_request_reads_csv(tmp_path):
    csv_path = tmp_path / "personas.csv"
    csv_path.write_text(
        "name,age,habits,weight\n"
        "Segment A,18-24,\"late night gaming\",0.5\n"
        "Segment B,25-34,\"morning workouts\",0.5\n",
        encoding="utf-8",
    )
    request = simple_interface.build_simple_request(
        concept_text="A new smart bottle.",
        persona_csv_path=csv_path,
        persona_group="us_toothpaste_buyers",
        samples_per_persona=25,
        total_samples=100,
    )
    assert isinstance(request, SimulationRequest)
    assert request.concept.text == "A new smart bottle."
    assert "Segment A" in (request.persona_csv or "")
    assert request.persona_group == "us_toothpaste_buyers"
    assert request.options.n == 25
    assert request.options.total_n == 100


def test_build_simple_request_requires_signal():
    with pytest.raises(ValueError):
        simple_interface.build_simple_request(
            concept_text="",
            concept_url=None,
        )


def test_run_simple_simulation_monkeypatched(monkeypatch):
    captured: dict[str, Any] = {}

    async def fake_run_simulation(request: SimulationRequest) -> SimulationResponse:
        captured["request"] = request
        aggregate = LikertDistribution(
            ratings=[1, 2, 3, 4, 5],
            pmf=[0.1, 0.2, 0.3, 0.2, 0.2],
            mean=3.2,
            top2box=0.4,
            sample_n=25,
        )
        persona = PersonaSpec(name="Test Persona", weight=1.0)
        result = PersonaResult(
            persona=persona,
            distribution=aggregate,
            rationales=["Great fit"],
            themes=["value"],
        )
        return SimulationResponse(
            aggregate=aggregate,
            personas=[result],
            metadata={"persona_summary": "Test Persona"},
        )

    monkeypatch.setattr(simple_interface, "run_simulation", fake_run_simulation)

    response = simple_interface.run_simple_simulation(
        concept_text="A premium sparkling water.",
        samples_per_persona=10,
    )

    assert response.aggregate.mean == 3.2
    assert captured["request"].concept.text == "A premium sparkling water."
