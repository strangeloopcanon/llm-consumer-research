#!/usr/bin/env python3
"""Build a persona CSV from a population spec.

Spec format (YAML or JSON):

base_group: us_toothpaste_buyers  # optional library seed
persona_csv_path: data/custom.csv  # optional additional CSV bucket
filters:
  - group: us_toothpaste_buyers
    include: { age: [25-44] }
    weight_share: 0.3
generations:
  - prompt: Eco-conscious professionals
    count: 2
    weight_share: 0.2
    attributes: { region: US }
injections:
  - persona:
      name: Custom Segment
      descriptors: [loyal, premium]
      weight: 1.0
    weight_share: 0.1
marginals:
  age: { "18-24": 0.12, "25-44": 0.36, "45-64": 0.32, "65+": 0.20 }
raking:
  enabled: true
  mode: lenient
  iterations: 25

Usage:
  python scripts/build_persona_csv.py --spec path/to/spec.yml --output /tmp/personas.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import yaml

from ssr_service.config import get_settings
from ssr_service.models import PersonaSpec, PopulationSpec
from ssr_service.personas import combine_persona_buckets, get_persona_library
from ssr_service.population import buckets_from_population_spec, rake_personas


def dump_csv(personas: Iterable[PersonaSpec], path: Path) -> None:
    import csv

    def join(values: List[str]) -> str:
        return ";".join(v for v in values if v)

    fieldnames = [
        "name",
        "age",
        "gender",
        "income",
        "region",
        "occupation",
        "education",
        "household",
        "purchase_frequency",
        "usage_context",
        "background",
        "habits",
        "motivations",
        "pain_points",
        "preferred_channels",
        "descriptors",
        "notes",
        "source",
        "weight",
    ]

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for persona in personas:
            writer.writerow(
                {
                    "name": persona.name,
                    "age": persona.age or "",
                    "gender": persona.gender or "",
                    "income": persona.income or "",
                    "region": persona.region or "",
                    "occupation": persona.occupation or "",
                    "education": persona.education or "",
                    "household": persona.household or "",
                    "purchase_frequency": persona.purchase_frequency or "",
                    "usage_context": persona.usage_context or "",
                    "background": persona.background or "",
                    "habits": join(persona.habits),
                    "motivations": join(persona.motivations),
                    "pain_points": join(persona.pain_points),
                    "preferred_channels": join(persona.preferred_channels),
                    "descriptors": join(persona.descriptors),
                    "notes": persona.notes or "",
                    "source": persona.source or "",
                    "weight": f"{persona.weight:.6f}",
                }
            )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Build persona CSV from population spec")
    parser.add_argument("--spec", type=Path, required=True, help="Spec YAML/JSON path")
    parser.add_argument("--output", type=Path, required=True, help="Destination CSV path")
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=None,
        help="Persona library directory (defaults to settings)",
    )
    args = parser.parse_args()

    settings = get_settings()
    library_dir = args.library_dir or Path(settings.persona_library_path)

    raw_text = args.spec.read_text(encoding="utf-8")
    try:
        payload = yaml.safe_load(raw_text)
    except Exception:
        payload = json.loads(raw_text)

    population_spec = PopulationSpec.model_validate(payload)
    library = get_persona_library(str(library_dir))

    buckets = await buckets_from_population_spec(population_spec, library, settings)
    if not buckets:
        raise SystemExit("Spec produced no personas; add base_group, filters, generations, or injections")

    personas = combine_persona_buckets(buckets)
    personas = rake_personas(personas, population_spec.marginals, population_spec.raking)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump_csv(personas, args.output)
    print(f"Wrote {len(personas)} personas to {args.output}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

