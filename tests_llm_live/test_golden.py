"""Live-style golden validation for SimulationResponse schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssr_service.models import SimulationResponse

GOLDEN_PATH = Path(__file__).with_name("goldens") / "example_response.json"


@pytest.mark.llm_live
def test_simulation_response_golden_shape() -> None:
    """Validate that the golden response conforms to the SimulationResponse schema."""
    data = json.loads(GOLDEN_PATH.read_text())
    response = SimulationResponse.model_validate(data)
    assert response.aggregate.sample_n > 0
    assert response.personas, "Expected at least one persona result"
    assert "model" in response.metadata
