"""Live-style golden validation for SimulationResponse schema."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from ssr_service.models import (
    ConceptInput,
    PersonaSpec,
    SimulationOptions,
    SimulationRequest,
    SimulationResponse,
)
from ssr_service.orchestrator import run_simulation

GOLDEN_PATH = Path(__file__).with_name("goldens") / "example_response.json"


@pytest.mark.llm_live
def test_simulation_response_golden_shape() -> None:
    """Validate that the golden response conforms to the SimulationResponse schema."""
    data = json.loads(GOLDEN_PATH.read_text())
    response = SimulationResponse.model_validate(data)
    assert response.aggregate.sample_n > 0
    assert response.personas, "Expected at least one persona result"
    assert "model" in response.metadata


@pytest.mark.llm_live
@pytest.mark.asyncio
async def test_openai_llm_live_smoke() -> None:
    """Exercise a real provider call when staging credentials are available."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is not configured")

    request = SimulationRequest(
        concept=ConceptInput(
            title="Live Test Toothpaste",
            text="A gentle whitening toothpaste for sensitive teeth.",
            price="$4.99",
        ),
        personas=[PersonaSpec(name="Thai Urban Parent", region="TH", weight=1.0)],
        questions=["คุณจะซื้อสินค้านี้ในเดือนนี้ไหม"],
        options=SimulationOptions(n=1, providers=["openai"], stratified=False),
    )

    start = time.perf_counter()
    response = await run_simulation(request)
    elapsed = time.perf_counter() - start
    max_seconds = float(os.getenv("LLM_LIVE_MAX_SECONDS", "90"))

    assert response.aggregate.sample_n == 1
    assert response.personas
    assert response.metadata.get("providers") == "openai"
    assert response.metadata.get("locale_detected") == "th-TH"
    assert elapsed <= max_seconds
