"""Population specification helpers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from .config import AppSettings
from .models import PersonaSpec, PopulationSpec, RakingConfig
from .persona_generation import synthesize_personas
from .personas import PersonaBucket, PersonaLibrary, filter_personas, personas_from_csv


async def buckets_from_population_spec(
    spec: PopulationSpec,
    library: PersonaLibrary,
    settings: AppSettings,
) -> List[PersonaBucket]:
    """Expand a population spec into persona buckets ready for blending."""

    buckets: List[PersonaBucket] = []

    if spec.base_group:
        group = library.get_group(spec.base_group)
        buckets.append(([p.model_copy(deep=True) for p in group.personas], None))

    if spec.persona_csv_path:
        csv_path = Path(spec.persona_csv_path)
        if not csv_path.exists():  # pragma: no cover - runtime guard
            raise FileNotFoundError(f"Persona CSV not found: {csv_path}")
        buckets.append((personas_from_csv(csv_path), None))

    for persona_filter in spec.filters:
        filtered = filter_personas(library, persona_filter)
        if filtered:
            buckets.append((filtered, persona_filter.weight_share))

    for generation in spec.generations:
        generated = await synthesize_personas(generation, settings)
        if generated:
            buckets.append((generated, generation.weight_share))

    for injection in spec.injections:
        buckets.append(([
            injection.persona.model_copy(deep=True)
        ], injection.weight_share))

    return buckets


def _category_value(persona: PersonaSpec, field: str) -> str | None:
    if not hasattr(persona, field):
        return None
    value = getattr(persona, field)
    if value is None or isinstance(value, list):
        return None
    text = str(value).strip()
    return text if text else None


def rake_personas(
    personas: Iterable[PersonaSpec],
    marginals: Dict[str, Dict[str, float]],
    config: RakingConfig,
) -> List[PersonaSpec]:
    """Adjust persona weights to match target marginals using iterative proportional fitting."""

    personas_list = [p.model_copy(deep=True) for p in personas]
    if not marginals or not config.enabled:
        total = sum(max(p.weight, 0.0) for p in personas_list) or 1.0
        for p in personas_list:
            p.weight = max(p.weight, 0.0) / total
        return personas_list

    # Normalize starting weights
    total = sum(max(p.weight, 0.0) for p in personas_list) or 1.0
    for p in personas_list:
        p.weight = max(p.weight, 0.0) / total

    targets = {
        field: {category: float(weight) for category, weight in buckets.items()}
        for field, buckets in marginals.items()
    }

    for _ in range(config.iterations):
        for field, buckets in targets.items():
            current_totals: Dict[str, float] = defaultdict(float)
            field_total = 0.0
            for persona in personas_list:
                category = _category_value(persona, field)
                if category is None:
                    continue
                current_totals[category] += persona.weight
                field_total += persona.weight

            if field_total <= 0:
                continue

            present_cats = {cat for cat, weight in current_totals.items() if weight > 0}
            if not present_cats:
                continue

            missing_required = [
                cat for cat, weight in buckets.items() if weight > 0 and cat not in present_cats
            ]
            if missing_required and config.mode == "strict":
                raise ValueError(
                    f"Raking failed: field '{field}' missing categories {missing_required}"
                )

            target_sum = sum(buckets.get(cat, 0.0) for cat in present_cats)
            if target_sum <= 0:
                continue

            adjustments: Dict[str, float] = {}
            for cat in present_cats:
                target_share = buckets.get(cat, 0.0) / target_sum
                current_share = current_totals.get(cat, 0.0) / field_total
                if current_share <= 0:
                    if config.mode == "strict" and target_share > 0:
                        raise ValueError(
                            f"Raking failed: category '{cat}' for field '{field}' has no personas"
                        )
                    adjustments[cat] = 1.0
                else:
                    adjustments[cat] = target_share / current_share

            for persona in personas_list:
                category = _category_value(persona, field)
                if category is None:
                    continue
                persona.weight *= adjustments.get(category, 1.0)

            total = sum(max(p.weight, 0.0) for p in personas_list) or 1.0
            for persona in personas_list:
                persona.weight = max(persona.weight, 0.0) / total

    total = sum(max(p.weight, 0.0) for p in personas_list) or 1.0
    for persona in personas_list:
        persona.weight = max(persona.weight, 0.0) / total

    return personas_list


__all__ = ["buckets_from_population_spec", "rake_personas"]
