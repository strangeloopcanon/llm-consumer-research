"""Persona library and ingestion helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

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


def load_persona_group(path: Path) -> PersonaGroup:
    with path.open("r", encoding="utf-8") as fp:
        raw = yaml.safe_load(fp)

    group_name = str(raw.get("group", path.stem))
    description = str(raw.get("description", ""))
    personas_data = raw.get("personas", [])

    personas: List[PersonaSpec] = []
    for entry in personas_data:
        personas.append(
            PersonaSpec(
                name=str(entry.get("name", "Persona")),
                age=str(entry.get("age", "")) or None,
                gender=str(entry.get("gender", "")) or None,
                income=str(entry.get("income", "")) or None,
                region=str(entry.get("region", "")) or None,
                descriptors=list(entry.get("descriptors", [])),
                weight=_coerce_float(entry.get("weight", 1.0)) or 1.0,
            )
        )

    if not personas:
        raise ValueError(f"Persona file {path} contains no personas")

    source = raw.get("source")
    return PersonaGroup(name=group_name, description=description, personas=personas, source=source)


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


def personas_from_csv(csv_source: Union[Path, str], encoding: str = "utf-8") -> List[PersonaSpec]:
    personas: List[PersonaSpec] = []
    if isinstance(csv_source, Path):
        fh = csv_source.open("r", encoding=encoding, newline="")
    else:
        fh = StringIO(csv_source)

    with fh:
        reader = csv.DictReader(fh)
        for row in reader:
            descriptors = row.get("descriptors") or row.get("traits") or ""
            descriptor_list = [d.strip() for d in descriptors.split(";") if d.strip()]
            personas.append(
                PersonaSpec(
                    name=row.get("name") or f"Persona {len(personas) + 1}",
                    age=row.get("age") or None,
                    gender=row.get("gender") or None,
                    income=row.get("income") or None,
                    region=row.get("region") or None,
                    descriptors=descriptor_list,
                    weight=_coerce_float(row.get("weight")) or 1.0,
                )
            )

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
