"""Anchor management for SSR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import yaml


@dataclass(slots=True)
class AnchorSet:
    """Hold anchor statements for a Likert intent."""

    id: str
    anchors: Mapping[int, str]

    def sorted_items(self) -> List[tuple[int, str]]:
        """Return anchors sorted by rating."""

        return sorted(self.anchors.items(), key=lambda item: item[0])


@dataclass(slots=True)
class AnchorBank:
    """Collection of anchor sets for a given intent."""

    version: str
    intent: str
    locale: str
    anchor_sets: List[AnchorSet]

    def ratings(self) -> Iterable[int]:
        """Return supported ratings."""

        if not self.anchor_sets:
            return []
        return sorted(self.anchor_sets[0].anchors.keys())


def load_anchor_bank(path: Path) -> AnchorBank:
    """Load anchor bank from YAML file."""

    with path.open("r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp)

    version = str(raw["version"])
    intent = str(raw["intent"])
    locale = str(raw.get("locale", "en-US"))

    anchor_sets: List[AnchorSet] = []
    for entry in raw.get("anchor_sets", []):
        anchors_dict: Dict[int, str] = {
            int(k): str(v) for k, v in entry.get("anchors", {}).items()
        }
        anchor_sets.append(AnchorSet(id=str(entry.get("id")), anchors=anchors_dict))

    if not anchor_sets:
        raise ValueError(f"Anchor file {path} contains no anchor sets")

    first_keys = set(anchor_sets[0].anchors.keys())
    for anchor_set in anchor_sets[1:]:
        if set(anchor_set.anchors.keys()) != first_keys:
            raise ValueError("Anchor sets must share identical rating keys")

    return AnchorBank(
        version=version, intent=intent, locale=locale, anchor_sets=anchor_sets
    )


__all__ = ["AnchorBank", "AnchorSet", "load_anchor_bank"]
