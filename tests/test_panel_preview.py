"""Tests for the /panel-preview orchestration helper."""

from __future__ import annotations

import pytest

from ssr_service.models import ConceptInput, SimulationOptions, SimulationRequest
from ssr_service.orchestrator import preview_panel


@pytest.mark.asyncio
async def test_preview_panel_resolves_panel_and_questions() -> None:
    request = SimulationRequest(
        concept=ConceptInput(),
        persona_group="us_toothpaste_buyers",
        options=SimulationOptions(n=10, stratified=False),
    )

    response = await preview_panel(request)

    assert response.panel
    assert sum(item.draws for item in response.panel) == 40
    assert response.questions

    q1 = response.questions[0]
    assert q1.id == "q1"
    assert q1.intent == "purchase_intent"
    assert q1.anchor_bank == "purchase_intent_en.yml"
    assert response.metadata["persona_total"] == str(len(response.panel))
