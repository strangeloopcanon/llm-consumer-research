"""Persona library and ingestion helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, TextIO, Tuple, Union

import yaml

from .models import PersonaFilter, PersonaSpec


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
                "context": _list_field(entry, "context"),
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
    for file in sorted(directory.glob("*.yml")):
        group = load_persona_group(file)
        library[group.name] = group
    return library


class PersonaLibrary:
    """Cached access to persona groups stored on disk."""

    def __init__(self, directory: Path):
        self._directory = directory
        self._groups: Dict[str, PersonaGroup] = {}
        self.reload()

    def reload(self) -> None:
        self._groups = load_library(self._directory)

    @property
    def directory(self) -> Path:
        return self._directory

    def groups(self) -> Dict[str, PersonaGroup]:
        return dict(self._groups)

    def get_group(self, name: str) -> PersonaGroup:
        try:
            return self._groups[name]
        except KeyError:
            self.reload()
            try:
                return self._groups[name]
            except KeyError as exc:  # pragma: no cover - defensive path
                raise KeyError(
                    f"Persona group '{name}' not found in {self._directory}"
                ) from exc

    def list_personas(self, group: Optional[str] = None) -> List[PersonaSpec]:
        if group:
            return [
                persona.model_copy(deep=True)
                for persona in self.get_group(group).personas
            ]
        personas: List[PersonaSpec] = []
        for grp in self._groups.values():
            personas.extend(p.model_copy(deep=True) for p in grp.personas)
        return personas


@lru_cache(maxsize=8)
def get_persona_library(directory: str) -> PersonaLibrary:
    """Return a cached PersonaLibrary for the provided directory path."""

    return PersonaLibrary(Path(directory))


def refresh_persona_library(directory: str) -> None:
    """Clear the cached PersonaLibrary for hot-reload scenarios."""

    _ = directory  # retained for API symmetry
    get_persona_library.cache_clear()


def get_persona_group(name: str, directory: Path) -> PersonaGroup:
    library = get_persona_library(str(directory))
    return library.get_group(name)


def _normalise_values(values: Iterable[str]) -> List[str]:
    normalised: List[str] = []
    for value in values:
        if value is None:
            continue
        cleaned = str(value).strip().lower()
        if cleaned:
            normalised.append(cleaned)
    return normalised


def _persona_field_values(persona: PersonaSpec, field: str) -> List[str]:
    if not hasattr(persona, field):
        return []
    raw = getattr(persona, field)
    if raw is None:
        return []
    if isinstance(raw, list):
        return _normalise_values(raw)
    return _normalise_values([raw])


def _persona_search_blob(persona: PersonaSpec) -> str:
    parts = [
        persona.name,
        persona.background or "",
        persona.notes or "",
        persona.describe(),
        " ".join(persona.descriptors),
        " ".join(persona.context),
        " ".join(persona.habits),
        " ".join(persona.motivations),
        " ".join(persona.pain_points),
        " ".join(persona.preferred_channels),
    ]
    return " ".join(filter(None, parts)).lower()


def filter_personas(
    library: PersonaLibrary, persona_filter: PersonaFilter
) -> List[PersonaSpec]:
    """Return personas that satisfy the provided filter."""

    candidates = library.list_personas(persona_filter.group)
    include = {k: set(_normalise_values(v)) for k, v in persona_filter.include.items()}
    exclude = {k: set(_normalise_values(v)) for k, v in persona_filter.exclude.items()}
    keywords = [kw.strip().lower() for kw in persona_filter.keywords if kw.strip()]

    matches: List[PersonaSpec] = []
    for persona in candidates:
        include_ok = True
        for field, allowed in include.items():
            values = set(_persona_field_values(persona, field))
            if not values & allowed:
                include_ok = False
                break
        if not include_ok:
            continue

        exclude_hit = False
        for field, banned in exclude.items():
            values = set(_persona_field_values(persona, field))
            if values & banned:
                exclude_hit = True
                break
        if exclude_hit:
            continue

        if keywords:
            blob = _persona_search_blob(persona)
            if any(keyword not in blob for keyword in keywords):
                continue

        matches.append(persona.model_copy(deep=True))

    if persona_filter.limit:
        matches = matches[: persona_filter.limit]

    return matches


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
                "context": _split_list(row.get("context")),
                "weight": _coerce_float(row.get("weight")) or 1.0,
            }
            personas.append(PersonaSpec.model_validate(persona_data))

    if not personas:
        raise ValueError("CSV did not yield any personas")

    return personas


def ensure_weights(
    personas: Iterable[PersonaSpec], target_total: float = 1.0
) -> List[PersonaSpec]:
    personas_list = [p for p in personas]
    total = sum(max(p.weight, 0.0) for p in personas_list)
    if total <= 0:
        n = len(personas_list)
        if n == 0:
            return personas_list
        equal = target_total / max(n, 1)
        for p in personas_list:
            p.weight = equal
        return personas_list

    if target_total <= 0:
        for p in personas_list:
            p.weight = 0.0
        return personas_list

    scale = target_total / total
    for p in personas_list:
        p.weight = max(p.weight, 0.0) * scale
    return personas_list


PersonaBucket = Tuple[List[PersonaSpec], Optional[float]]


def combine_persona_buckets(buckets: Iterable[PersonaBucket]) -> List[PersonaSpec]:
    """Blend persona lists into a single normalised set.

    Each bucket is a tuple of (personas, weight_share). When weight_share is provided,
    the personas within that bucket are normalised to the requested share. Buckets
    without a share divide the remaining weight proportionally.
    """

    buckets_list = [(list(personas), share) for personas, share in buckets]
    specified = [(ps, share) for ps, share in buckets_list if share is not None]
    unspecified = [(ps, share) for ps, share in buckets_list if share is None]

    specified_total = sum(share for _, share in specified)
    if specified_total > 1.0 + 1e-6:
        raise ValueError(
            "Persona weight shares exceed 1.0; adjust weight_share values to fit."
        )

    combined: Dict[str, PersonaSpec] = {}

    def _accumulate(persona_list: List[PersonaSpec]) -> None:
        for persona in persona_list:
            existing = combined.get(persona.name)
            if existing:
                existing.weight += persona.weight
            else:
                combined[persona.name] = persona

    for personas, share in specified:
        if not personas:
            continue
        prepared = ensure_weights(
            [p.model_copy(deep=True) for p in personas], target_total=share or 0.0
        )
        _accumulate(prepared)

    if unspecified:
        remaining = max(1.0 - specified_total, 0.0)
        raw_total = sum(
            sum(max(p.weight, 0.0) for p in persons) for persons, _ in unspecified
        )
        if remaining > 0 and raw_total > 0:
            for personas, _ in unspecified:
                bucket_weight = sum(max(p.weight, 0.0) for p in personas)
                share = remaining * (bucket_weight / raw_total) if bucket_weight else 0.0
                prepared = ensure_weights(
                    [p.model_copy(deep=True) for p in personas], target_total=share
                )
                _accumulate(prepared)
        # If no remaining share is available, the unspecified buckets are ignored.

    final_personas = list(combined.values())
    total_weight = sum(max(p.weight, 0.0) for p in final_personas)
    if total_weight <= 0:
        return final_personas

    scale = 1.0 / total_weight
    for persona in final_personas:
        persona.weight = max(persona.weight, 0.0) * scale
    return final_personas


__all__ = [
    "PersonaBucket",
    "PersonaGroup",
    "PersonaLibrary",
    "combine_persona_buckets",
    "ensure_weights",
    "filter_personas",
    "get_persona_group",
    "get_persona_library",
    "load_library",
    "load_persona_group",
    "personas_from_csv",
]
