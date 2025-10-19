"""Command-line entry point that wraps the simplified simulation helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .simple_interface import run_simple_simulation


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a synthetic survey using the simplified interface.",
    )
    parser.add_argument("--concept-text", required=False, help="Concept description.")
    parser.add_argument("--concept-url", help="Optional URL for the concept.")
    parser.add_argument("--title", help="Concept title.", default=None)
    parser.add_argument("--price", help="Price or offer framing.", default=None)
    parser.add_argument(
        "--persona-group",
        help="Name of a persona group defined in the library.",
        default=None,
    )
    parser.add_argument(
        "--persona-csv",
        type=Path,
        help="Path to a persona CSV file with columns like name,age,habits.",
    )
    parser.add_argument(
        "--samples-per-persona",
        type=int,
        default=50,
        help="Number of synthetic respondents per persona.",
    )
    parser.add_argument(
        "--total-samples",
        type=int,
        default=None,
        help="Total synthetic respondents across personas (optional).",
    )
    parser.add_argument(
        "--no-stratified",
        action="store_true",
        help="Disable stratified allocation when total samples are provided.",
    )
    parser.add_argument(
        "--intent-question",
        help="Override the default intent question.",
        default=None,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response instead of a human summary.",
    )
    return parser


def _print_human_summary(response: Any) -> None:
    aggregate = response["aggregate"]
    print("=== Aggregate ===")
    print(f"Mean: {aggregate['mean']:.2f}")
    print(f"Top-2 box: {aggregate['top2box']:.1%}")
    print(f"Sample size: {aggregate['sample_n']}")
    print()
    print("=== Personas ===")
    for persona_result in response["personas"]:
        persona = persona_result["persona"]
        distribution = persona_result["distribution"]
        print(f"- {persona['name']} (weight {persona['weight']:.0%})")
        traits = [
            part
            for part in [
                persona.get("age"),
                persona.get("region"),
                persona.get("occupation"),
            ]
            if part
        ]
        if traits:
            print(f"  Traits: {', '.join(traits)}")
        if persona.get("habits"):
            print(f"  Habits: {', '.join(persona['habits'][:2])}")
        print(
            f"  Mean {distribution['mean']:.2f} | Top-2 {distribution['top2box']:.1%}"
        )
        themes = persona_result.get("themes") or []
        if themes:
            print(f"  Themes: {', '.join(themes)}")
        print()
    print("=== Metadata ===")
    for key, value in response.get("metadata", {}).items():
        print(f"{key}: {value}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    response = run_simple_simulation(
        concept_text=args.concept_text or "",
        concept_url=args.concept_url,
        title=args.title,
        price=args.price,
        persona_group=args.persona_group,
        persona_csv_path=args.persona_csv,
        samples_per_persona=args.samples_per_persona,
        total_samples=args.total_samples,
        stratified=not args.no_stratified,
        intent_question=args.intent_question,
    )

    response_dict = response.model_dump()
    if args.json:
        print(json.dumps(response_dict, indent=2))
    else:
        _print_human_summary(response_dict)


if __name__ == "__main__":
    main()
