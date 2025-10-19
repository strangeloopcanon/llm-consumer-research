"""Persona library and ingestion helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TextIO, Union

import yaml

from .models import PersonaSpec


@dataclass(slots=True)
class PersonaGroup:
    name: str
    description: str
    personas: List[PersonaSpec]
    source: Optional[str] = None


def _coerce_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_str(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value).strip() or None


def load_persona_group(path: Path) -> PersonaGroup:
    with path.open("r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp)

    group_name = str(raw.get("group", path.stem))
    description = str(raw.get("description", ""))
    personas_data = raw.get("personas", [])

    def _list_field(entry: dict, key: str) -> List[str]:
        value = entry.get(key, [])
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(";") if item.strip()]
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return []

    personas: List[PersonaSpec] = []
    for entry in personas_data:
        persona_data = {
            "name": _coerce_str(entry.get("name")) or "Persona",
            "age": _coerce_str(entry.get("age")),
            "gender": _coerce_str(entry.get("gender")),
            "income": _coerce_str(entry.get("income")),
            "region": _coerce_str(entry.get("region")),
            "occupation": _coerce_str(entry.get("occupation")),
            "education": _coerce_str(entry.get("education")),
            "household": _coerce_str(entry.get("household")),
            "purchase_frequency": _coerce_str(
                entry.get("purchase_frequency") or entry.get("purchase_freq")
            ),
            "usage_context": _coerce_str(
                entry.get("usage") or entry.get("usage_context")
            ),
            "background": _coerce_str(entry.get("background")),
            "habits": _list_field(entry, "habits"),
            "motivations": _list_field(entry, "motivations"),
            "pain_points": _list_field(entry, "pain_points"),
            "preferred_channels": _list_field(entry, "preferred_channels"),
            "notes": _coerce_str(entry.get("notes")),
            "source": _coerce_str(entry.get("persona_source") or entry.get("source")),
            "descriptors": _list_field(entry, "descriptors"),
            "weight": _coerce_float(entry.get("weight", 1.0)) or 1.0,
        }
        personas.append(PersonaSpec.model_validate(persona_data))

    if not personas:
        raise ValueError(f"Persona file {path} contains no personas")

    source = raw.get("source")
    return PersonaGroup(
        name=group_name, description=description, personas=personas, source=source
    )


def load_library(directory: Path) -> Dict[str, PersonaGroup]:
    library: Dict[str, PersonaGroup] = {}
    for file in directory.glob("*.yml"):
        group = load_persona_group(file)
        library[group.name] = group
    return library


def get_persona_group(name: str, directory: Path) -> PersonaGroup:
    for file in directory.glob("*.yml"):
        group = load_persona_group(file)
        if group.name == name:
            return group
    raise KeyError(f"Persona group '{name}' not found in {directory}")


def personas_from_csv(
    csv_source: Union[Path, str], encoding: str = "utf-8"
) -> List[PersonaSpec]:
    personas: List[PersonaSpec] = []
    fh: TextIO
    if isinstance(csv_source, Path):
        fh = csv_source.open("r", encoding=encoding, newline="")
    else:
        fh = StringIO(csv_source)

    with fh:
        reader = csv.DictReader(fh)

        def _split_list(value: Optional[str]) -> List[str]:
            if not value:
                return []
            return [item.strip() for item in value.split(";") if item.strip()]

        for row in reader:
            persona_data = {
                "name": row.get("name") or f"Persona {len(personas) + 1}",
                "age": row.get("age") or None,
                "gender": row.get("gender") or None,
                "income": row.get("income") or None,
                "region": row.get("region") or None,
                "occupation": row.get("occupation") or None,
                "education": row.get("education") or None,
                "household": row.get("household") or None,
                "purchase_frequency": row.get("purchase_frequency")
                or row.get("purchase_freq")
                or None,
                "usage_context": row.get("usage") or row.get("usage_context") or None,
                "background": row.get("background") or None,
                "habits": _split_list(row.get("habits")),
                "motivations": _split_list(row.get("motivations")),
                "pain_points": _split_list(row.get("pain_points")),
                "preferred_channels": _split_list(row.get("preferred_channels")),
                "notes": row.get("notes") or None,
                "source": row.get("persona_source") or row.get("source") or None,
                "descriptors": _split_list(row.get("descriptors") or row.get("traits")),
                "weight": _coerce_float(row.get("weight")) or 1.0,
            }
            personas.append(PersonaSpec.model_validate(persona_data))

    if not personas:
        raise ValueError("CSV did not yield any personas")

    return personas


def ensure_weights(personas: Iterable[PersonaSpec]) -> List[PersonaSpec]:
    personas_list = list(personas)
    total = sum(p.weight for p in personas_list)
    if total <= 0:
        n = len(personas_list)
        for p in personas_list:
            p.weight = 1.0 / max(n, 1)
        return personas_list

    for p in personas_list:
        p.weight = p.weight / total
    return personas_list


__all__ = [
    "PersonaGroup",
    "load_persona_group",
    "load_library",
    "get_persona_group",
    "personas_from_csv",
    "ensure_weights",
]
