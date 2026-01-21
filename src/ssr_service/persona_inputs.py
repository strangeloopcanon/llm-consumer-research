"""Parsing helpers for persona filter/generation/injection expressions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import (
    PersonaFilter,
    PersonaGenerationTask,
    PersonaInjection,
    PersonaSpec,
    PopulationSpec,
    QuestionSpec,
)


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_filter_expression(expr: str) -> PersonaFilter:
    if not expr:
        raise ValueError("persona-filter expression cannot be empty")

    include: Dict[str, List[str]] = {}
    exclude: Dict[str, List[str]] = {}
    keywords: List[str] = []
    group: str | None = None
    limit: int | None = None
    weight_share: float | None = None

    for token in (part.strip() for part in expr.split(";") if part.strip()):
        if "=" not in token:
            continue
        key, raw_value = token.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if key == "group":
            group = raw_value or None
        elif key.startswith("include."):
            field = key.split(".", 1)[1]
            include.setdefault(field, []).extend(_split_csv(raw_value))
        elif key.startswith("exclude."):
            field = key.split(".", 1)[1]
            exclude.setdefault(field, []).extend(_split_csv(raw_value))
        elif key in {"keyword", "keywords"}:
            values = _split_csv(raw_value)
            keywords.extend(values or [raw_value])
        elif key == "limit":
            limit = int(raw_value)
        elif key in {"share", "weight_share"}:
            weight_share = float(raw_value)

    if include and exclude and any(field in include for field in exclude):
        raise ValueError("persona-filter cannot include and exclude the same field")

    return PersonaFilter(
        group=group,
        include=include,
        exclude=exclude,
        keywords=keywords,
        limit=limit,
        weight_share=weight_share,
    )


def parse_generation_expression(expr: str) -> PersonaGenerationTask:
    if not expr:
        raise ValueError("persona-generation expression cannot be empty")

    prompt: str | None = None
    count: int | None = None
    strategy = "heuristic"
    weight_share: float | None = None
    attributes: Dict[str, str] = {}

    for token in (part.strip() for part in expr.split(";") if part.strip()):
        if "=" not in token:
            continue
        key, raw_value = token.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if key == "prompt":
            prompt = raw_value
        elif key == "count":
            count = int(raw_value)
        elif key in {"strategy", "backend"}:
            if raw_value not in {"heuristic", "openai"}:
                raise ValueError("persona-generation strategy must be 'heuristic' or 'openai'")
            strategy = raw_value
        elif key in {"share", "weight_share"}:
            weight_share = float(raw_value)
        elif key.startswith("attr."):
            field = key.split(".", 1)[1]
            attributes[field] = raw_value

    if not prompt:
        raise ValueError("persona-generation expression requires a prompt=<text>")

    return PersonaGenerationTask(
        prompt=prompt,
        count=count or 1,
        strategy=strategy,  # type: ignore[arg-type]
        weight_share=weight_share,
        attributes=attributes,
    )


def parse_injection_payload(expr: str) -> PersonaInjection:
    if not expr:
        raise ValueError("persona-injection payload cannot be empty")

    potential_path = Path(expr)
    data: Dict[str, Any]
    if potential_path.exists():
        data = json.loads(potential_path.read_text(encoding="utf-8"))
    else:
        try:
            data = json.loads(expr)
        except json.JSONDecodeError:
            data = {}
            weight_share: float | None = None
            for token in (part.strip() for part in expr.split(";") if part.strip()):
                if "=" not in token:
                    continue
                key, raw_value = token.split("=", 1)
                key = key.strip()
                raw_value = raw_value.strip()
                if key in {"share", "weight_share"}:
                    weight_share = float(raw_value)
                    data["weight_share"] = weight_share
                    continue
                persona_payload = data.setdefault("persona", {})
                if key in {
                    "context",
                    "habits",
                    "motivations",
                    "pain_points",
                    "preferred_channels",
                    "descriptors",
                }:
                    persona_payload[key] = _split_csv(raw_value)
                elif key == "weight":
                    persona_payload[key] = float(raw_value)
                else:
                    persona_payload[key] = raw_value

    persona_payload = data.get("persona", data)
    weight_share = data.get("weight_share")
    persona = PersonaSpec.model_validate(persona_payload)
    return PersonaInjection(persona=persona, weight_share=weight_share)


def parse_population_spec_input(expr: str) -> PopulationSpec:
    if not expr:
        raise ValueError("population spec input cannot be empty")

    candidate = expr.strip()
    if not candidate:
        raise ValueError("population spec input cannot be empty")

    path = Path(candidate)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = expr

    try:
        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)

    if data is None:
        raise ValueError("population spec input did not contain data")

    return PopulationSpec.model_validate(data)


def parse_question_spec_expression(expr: str) -> QuestionSpec:
    if not expr:
        raise ValueError("question-spec expression cannot be empty")

    question_id: str | None = None
    text: str | None = None
    intent: str | None = None
    anchor_bank: str | None = None

    for token in (part.strip() for part in expr.split(";") if part.strip()):
        if "=" not in token:
            continue
        key, raw_value = token.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if key in {"id", "qid", "question_id"}:
            question_id = raw_value or None
        elif key in {"text", "question"}:
            text = raw_value
        elif key == "intent":
            intent = raw_value or None
        elif key in {"anchor", "anchor_bank"}:
            anchor_bank = raw_value or None

    if not text:
        raise ValueError("question-spec expression requires text=<question>")

    return QuestionSpec(
        id=question_id,
        text=text,
        intent=intent,
        anchor_bank=anchor_bank,
    )


__all__ = [
    "parse_filter_expression",
    "parse_generation_expression",
    "parse_injection_payload",
    "parse_population_spec_input",
    "parse_question_spec_expression",
]
