"""Tests for persona enrichment helpers."""

from __future__ import annotations

from ssr_service.models import LikertDistribution, PersonaResult, PersonaSpec
from ssr_service.orchestrator import _summarize_personas
from ssr_service.personas import personas_from_csv


def test_persona_spec_describe_includes_enriched_fields():
    persona = PersonaSpec(
        name="Efficiency-Seeking Manager",
        age="35-44",
        gender="female",
        region="US",
        occupation="Operations manager",
        background="Runs cross-functional teams in a hybrid office.",
        habits=["reviews dashboards nightly", "crowdsources tool tips"],
        motivations=["wants time savings", "values reliable partners"],
    )
    description = persona.describe()
    assert "Operations manager" in description
    assert "habits" in description
    assert "motivations" in description


def test_personas_from_csv_parses_enriched_columns(tmp_path):
    csv_path = tmp_path / "panel.csv"
    csv_path.write_text(
        "name,age,habits,motivations,preferred_channels,weight\n"
        "Segment A,25-34,\"night runs;podcasts\",\"brand trust\",\"Email;Mobile\",0.4\n"
        "Segment B,35-44,\"family errands\",\"budget hunts\",\"Retail\",0.6\n",
        encoding="utf-8",
    )
    personas = personas_from_csv(csv_path)
    assert personas[0].habits == ["night runs", "podcasts"]
    assert personas[0].motivations == ["brand trust"]
    assert personas[0].preferred_channels == ["Email", "Mobile"]
    assert personas[1].habits == ["family errands"]


def test_persona_summary_highlights_key_traits():
    persona = PersonaSpec(
        name="Urban Creator",
        age="25-34",
        region="US-West",
        occupation="Content creator",
        habits=["streams daily", "tests gadgets"],
        motivations=["wants speed"],
        preferred_channels=["YouTube"],
        weight=0.5,
    )
    distribution = LikertDistribution(
        ratings=[1, 2, 3, 4, 5],
        pmf=[0.1, 0.2, 0.3, 0.3, 0.1],
        mean=3.2,
        top2box=0.4,
        sample_n=10,
    )
    result = PersonaResult(
        persona=persona,
        distribution=distribution,
        rationales=[],
        themes=[],
    )
    summary = _summarize_personas([result])
    assert "Urban Creator" in summary
    assert "Content creator" in summary
    assert "habits" in summary
