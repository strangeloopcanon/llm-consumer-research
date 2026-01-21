"""Command-line entry point that wraps the simplified simulation helpers."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from .models import (
    ConceptInput,
    PanelContextSpec,
    QuestionSpec,
    SimulationOptions,
    SimulationRequest,
    coerce_http_url,
)
from .orchestrator import preview_panel
from .persona_inputs import (
    parse_filter_expression,
    parse_generation_expression,
    parse_injection_payload,
    parse_population_spec_input,
    parse_question_spec_expression,
)
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
        "--persona-filter",
        action="append",
        help=(
            "Persona filter expression (e.g. 'group=us_toothpaste_buyers;"
            "include.age=25-44;keyword=family;share=0.5'). Repeatable."
        ),
    )
    parser.add_argument(
        "--persona-generation",
        action="append",
        help=(
            "Persona generation expression (e.g. 'prompt=Eco parents;count=2;"
            "share=0.3;attr.region=US'). Repeatable."
        ),
    )
    parser.add_argument(
        "--persona-injection",
        action="append",
        help=(
            "Custom persona definition as JSON, file path, or expression "
            "(e.g. 'name=Custom;descriptors=loyal,premium;share=0.2')."
        ),
    )
    parser.add_argument(
        "--question",
        action="append",
        help="Additional question to ask (repeat flag for multiple questions).",
    )
    parser.add_argument(
        "--question-spec",
        action="append",
        help=(
            "Question spec expression (e.g. 'text=How much do you trust this?;"
            "intent=trust;anchor_bank=trust_en.yml'). Repeatable."
        ),
    )
    parser.add_argument(
        "--questionnaire",
        type=Path,
        default=None,
        help="Path to a YAML/JSON file containing a list of question specs.",
    )
    parser.add_argument(
        "--population-spec",
        help=(
            "Population spec as file path or inline YAML/JSON defining base group,"
            " slices, generations, injections, and marginals."
        ),
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
        "--seed",
        type=int,
        default=0,
        help="Base seed for panel reuse and deterministic sampling.",
    )
    parser.add_argument(
        "--panel-context",
        default=None,
        help="Behavioral context notes (inline text or path to a file).",
    )
    parser.add_argument(
        "--panel-context-mode",
        default="shared",
        choices=["shared", "round_robin", "sample"],
        help="How to allocate panel context chunks across personas.",
    )
    parser.add_argument(
        "--panel-context-per-persona",
        type=int,
        default=3,
        help="How many context chunks to attach to each persona (0 disables).",
    )
    parser.add_argument(
        "--include-respondents",
        action="store_true",
        help="Include respondent-level records in the JSON response.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response instead of a human summary.",
    )
    parser.add_argument(
        "--panel-preview",
        action="store_true",
        help="Preview the resolved panel + questions without calling LLMs.",
    )
    parser.add_argument(
        "--provider",
        action="append",
        help="LLM provider to use (e.g. openai, anthropic). Repeatable. Default: openai.",
    )
    return parser


def _print_human_summary(response: Any) -> None:
    aggregate = response["aggregate"]
    print("=== Aggregate ===")
    print(f"Mean: {aggregate['mean']:.2f}")
    print(f"Top-2 box: {aggregate['top2box']:.1%}")
    print(f"Sample size: {aggregate['sample_n']}")
    if response.get("questions"):
        print()
        print("=== Questions ===")
        for question in response["questions"]:
            dist = question["aggregate"]
            print(f"- {question['question_id']}: {question['question']}")
            print(f"  Mean {dist['mean']:.2f} | Top-2 {dist['top2box']:.1%}")
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


def _load_questionnaire(path: Path) -> list[QuestionSpec]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return []
    if isinstance(data, dict):
        data = data.get("questionnaire") or data.get("questions") or []
    if not isinstance(data, list):
        raise ValueError("questionnaire file must contain a list of question specs")
    return [QuestionSpec.model_validate(item) for item in data]


def _print_panel_preview(response: Any) -> None:
    print("=== Panel Preview ===")
    for item in response.get("panel", []):
        persona = item["persona"]
        draws = item["draws"]
        print(f"- {persona['name']} (weight {persona['weight']:.0%}) -> draws {draws}")
    print()
    print("=== Questions ===")
    for spec in response.get("questions", []):
        print(f"- {spec.get('id')}: {spec['text']} [{spec.get('intent')}]")
    print()
    print("=== Metadata ===")
    for key, value in response.get("metadata", {}).items():
        print(f"{key}: {value}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        persona_filters = [
            parse_filter_expression(expr) for expr in (args.persona_filter or [])
        ]
        persona_generations = [
            parse_generation_expression(expr)
            for expr in (args.persona_generation or [])
        ]
        persona_injections = [
            parse_injection_payload(expr) for expr in (args.persona_injection or [])
        ]
        population_spec = (
            parse_population_spec_input(args.population_spec)
            if args.population_spec
            else None
        )
        questions = [q.strip() for q in (args.question or []) if q and q.strip()]
        questionnaire: list[QuestionSpec] = []
        if args.questionnaire:
            questionnaire.extend(_load_questionnaire(args.questionnaire))
        if args.question_spec:
            questionnaire.extend(
                parse_question_spec_expression(expr)
                for expr in (args.question_spec or [])
            )
    except ValueError as exc:  # pragma: no cover - exercised via CLI usage
        parser.error(str(exc))

    panel_context: PanelContextSpec | None = None
    if args.panel_context:
        candidate_path = Path(args.panel_context)
        context_text = (
            candidate_path.read_text(encoding="utf-8")
            if candidate_path.exists()
            else args.panel_context
        )
        panel_context = PanelContextSpec(
            text=context_text,
            mode=args.panel_context_mode,
            chunks_per_persona=args.panel_context_per_persona,
        )

    if args.panel_preview:
        csv_data = (
            args.persona_csv.read_text(encoding="utf-8")
            if args.persona_csv is not None
            else None
        )
        request = SimulationRequest(
            concept=ConceptInput(
                title=args.title or None,
                text=(args.concept_text or "").strip() or None,
                price=args.price or None,
                url=coerce_http_url(args.concept_url),
            ),
            persona_group=args.persona_group,
            persona_csv=csv_data,
            persona_filters=persona_filters,
            persona_generations=persona_generations,
            persona_injections=persona_injections,
            population_spec=population_spec,
            questions=questions,
            questionnaire=questionnaire,
            intent_question=args.intent_question,
            options=SimulationOptions(
                n=args.samples_per_persona,
                total_n=args.total_samples,
                stratified=not args.no_stratified,
                providers=args.provider or ["openai"],
                include_respondents=args.include_respondents,
                seed=args.seed,
            ),
            panel_context=panel_context,
        )
        preview = asyncio.run(preview_panel(request))
        response_dict = preview.model_dump()
        if args.json:
            print(json.dumps(response_dict, indent=2))
        else:
            _print_panel_preview(response_dict)
        return

    response = run_simple_simulation(
        concept_text=args.concept_text or "",
        concept_url=args.concept_url,
        title=args.title,
        price=args.price,
        persona_group=args.persona_group,
        persona_csv_path=args.persona_csv,
        persona_filters=persona_filters,
        persona_generations=persona_generations,
        persona_injections=persona_injections,
        population_spec=population_spec,
        questions=questions,
        questionnaire=questionnaire,
        samples_per_persona=args.samples_per_persona,
        total_samples=args.total_samples,
        stratified=not args.no_stratified,
        intent_question=args.intent_question,
        providers=args.provider,
        include_respondents=args.include_respondents,
        seed=args.seed,
        panel_context=panel_context,
    )

    response_dict = response.model_dump()
    if args.json:
        print(json.dumps(response_dict, indent=2))
    else:
        _print_human_summary(response_dict)


if __name__ == "__main__":
    main()
