"""Tests for the orchestrator module."""

from __future__ import annotations

from ssr_service.config import AppSettings
from ssr_service.models import ConceptInput, SimulationOptions, SimulationRequest
from ssr_service.orchestrator import (
    _build_question_specs,
    _default_question,
    _infer_locale_from_request,
)


def test_default_question():
    """Test the _default_question function."""
    assert (
        _default_question("purchase_intent")
        == "How likely would you be to purchase this product?"
    )
    assert _default_question("relevance") == "How relevant is this concept to your needs?"
    assert _default_question("unknown") == "How do you feel about this offering?"


def test_infer_locale_from_request_detects_thai_market_signals():
    request = SimulationRequest(
        concept=ConceptInput(text="ยาสีฟันสูตรอ่อนโยนสำหรับครอบครัว"),
        questions=["คุณจะซื้อสินค้านี้หรือไม่"],
    )
    assert _infer_locale_from_request(request) == "th-TH"


def test_build_question_specs_uses_thai_anchor_when_locale_is_th():
    request = SimulationRequest(
        concept=ConceptInput(text="Thai market concept"),
        questions=[],
        options=SimulationOptions(),
    )
    settings = AppSettings()
    specs = _build_question_specs(
        request,
        request.options,
        locale="th-TH",
        settings=settings,
    )
    assert specs[0].anchor_bank == "purchase_intent_th.yml"


def test_build_question_specs_uses_english_anchor_when_locale_is_en():
    request = SimulationRequest(
        concept=ConceptInput(text="US market concept"),
        questions=[],
        options=SimulationOptions(),
    )
    settings = AppSettings()
    specs = _build_question_specs(
        request,
        request.options,
        locale="en-US",
        settings=settings,
    )
    assert specs[0].anchor_bank == "purchase_intent_en.yml"
