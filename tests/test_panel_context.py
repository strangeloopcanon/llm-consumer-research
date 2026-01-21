"""Unit tests for panel context chunking and allocation."""

from __future__ import annotations

from ssr_service.models import PanelContextSpec, PersonaSpec
from ssr_service.panel_context import apply_panel_context, chunk_context_text


def test_chunk_context_text_splits_bullets() -> None:
    text = "- Shops on Amazon\n- Looks for coupons\n"
    assert chunk_context_text(text) == ["Shops on Amazon", "Looks for coupons"]


def test_apply_panel_context_round_robin() -> None:
    personas = [PersonaSpec(name="A"), PersonaSpec(name="B")]
    spec = PanelContextSpec(
        text="- one\n- two\n- three\n- four\n",
        mode="round_robin",
        chunks_per_persona=2,
    )

    available = apply_panel_context(personas, spec, seed=0)

    assert available == 4
    assert personas[0].context == ["one", "two"]
    assert personas[1].context == ["three", "four"]


def test_apply_panel_context_sample_is_deterministic() -> None:
    spec = PanelContextSpec(
        chunks=["alpha", "bravo", "charlie", "delta"],
        mode="sample",
        chunks_per_persona=2,
    )

    personas_a = [PersonaSpec(name="A"), PersonaSpec(name="B")]
    personas_b = [PersonaSpec(name="A"), PersonaSpec(name="B")]

    apply_panel_context(personas_a, spec, seed=42)
    apply_panel_context(personas_b, spec, seed=42)

    assert [p.context for p in personas_a] == [p.context for p in personas_b]
