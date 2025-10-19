"""Tests for the orchestrator module."""

from __future__ import annotations

from ssr_service.orchestrator import _default_question


def test_default_question():
    """Test the _default_question function."""
    assert (
        _default_question("purchase_intent")
        == "How likely would you be to purchase this product?"
    )
    assert _default_question("relevance") == "How relevant is this concept to your needs?"
    assert _default_question("unknown") == "How do you feel about this offering?"
