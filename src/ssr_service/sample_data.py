"""Sample data utilities for default demo scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .config import get_settings


@dataclass(slots=True)
class SampleScenario:
    sample_id: str
    title: str
    description: str
    price: Optional[str]
    category: Optional[str]
    persona_group: Optional[str]
    intent_question: Optional[str]
    image: Optional[str]
    source: Optional[str]
    rating: Optional[Dict[str, float]]


_SAMPLES_CACHE: Dict[str, SampleScenario] | None = None


def _load_samples() -> Dict[str, SampleScenario]:
    global _SAMPLES_CACHE
    if _SAMPLES_CACHE is not None:
        return _SAMPLES_CACHE

    settings = get_settings()
    samples_path = Path(settings.anchor_bank_path).parent / "samples" / "demo_samples.json"
    with samples_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    samples: Dict[str, SampleScenario] = {}
    for item in data.get("samples", []):
        scenario = SampleScenario(
            sample_id=item["id"],
            title=item["title"],
            description=item["description"],
            price=item.get("price"),
            category=item.get("category"),
            persona_group=item.get("persona_group"),
            intent_question=item.get("intent_question"),
            image=item.get("image"),
            source=item.get("source"),
            rating=item.get("rating"),
        )
        samples[scenario.sample_id] = scenario

    _SAMPLES_CACHE = samples
    return samples


def get_sample_ids() -> Dict[str, str]:
    samples = _load_samples()
    return {sample_id: scenario.title for sample_id, scenario in samples.items()}


def load_sample(sample_id: str) -> SampleScenario:
    samples = _load_samples()
    if sample_id not in samples:
        raise KeyError(f"Sample '{sample_id}' not found")
    return samples[sample_id]


def default_sample() -> Optional[SampleScenario]:
    samples = _load_samples()
    return next(iter(samples.values()), None)


__all__ = ["SampleScenario", "get_sample_ids", "load_sample", "default_sample"]
