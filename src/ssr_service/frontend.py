"""Gradio frontend for running simulations interactively."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import altair as alt
import gradio as gr
import pandas as pd

from .config import get_settings
from .models import (
    ConceptInput,
    PersonaFilter,
    PersonaGenerationTask,
    PersonaInjection,
    SimulationOptions,
    SimulationRequest,
    SimulationResponse,
    coerce_http_url,
)
from .orchestrator import run_simulation
from .persona_inputs import (
    parse_filter_expression,
    parse_generation_expression,
    parse_injection_payload,
    parse_population_spec_input,
)
from .personas import load_library
from .sample_data import default_sample, get_sample_ids, load_sample

SETTINGS = get_settings()
PERSONA_LIBRARY = load_library(Path(SETTINGS.persona_library_path))


def _read_file(file_obj: Optional[Any]) -> Optional[str]:
    if file_obj is None:
        return None
    read_method = getattr(file_obj, "read", None)
    if not callable(read_method):
        return None
    content = read_method()
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return str(content)


def _make_markdown(response: SimulationResponse) -> str:
    aggregate = response.aggregate
    md_lines = [
        "### Aggregate Results",
        f"- Mean Likert: **{aggregate.mean:.2f}**",
        f"- Top-2 box: **{aggregate.top2box:.2%}**",
        f"- Sample size (synthetic): {aggregate.sample_n}",
        "",
    ]

    md_lines.append("#### Distribution")
    md_lines.append("| Rating | Probability |")
    md_lines.append("| --- | --- |")
    for rating, prob in zip(aggregate.ratings, aggregate.pmf):
        md_lines.append(f"| {rating} | {prob:.2%} |")

    md_lines.append("\n### Persona Segments")
    for persona_result in response.personas:
        persona = persona_result.persona
        dist = persona_result.distribution
        md_lines.append(
            f"**{persona.name}** (weight: {persona.weight:.0%}, n={dist.sample_n})"
        )
        themes = ", ".join(persona_result.themes) or "n/a"
        md_lines.append(
            f"- Mean: {dist.mean:.2f}, Top-2: {dist.top2box:.2%}, Themes: {themes}"
        )
        bullets = persona_result.rationales[:2]
        if bullets:
            md_lines.append("  - " + bullets[0])
            if len(bullets) > 1:
                md_lines.append("  - " + bullets[1])
        md_lines.append("")

    return "\n".join(md_lines)


def _persona_table(response: SimulationResponse) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for persona_result in response.personas:
        persona = persona_result.persona
        dist = persona_result.distribution
        rows.append(
            [
                persona.name,
                persona.weight,
                persona.age or "",
                persona.region or "",
                persona.income or "",
                dist.sample_n,
                dist.mean,
                dist.top2box,
                ", ".join(persona_result.themes),
            ]
        )
    return rows


def _metadata(response: SimulationResponse) -> Dict[str, str]:
    return response.metadata


def _plot_distribution(response: SimulationResponse) -> alt.Chart:
    """Create a layered bar and text chart of the aggregate distribution."""
    df = pd.DataFrame(
        {
            "rating": response.aggregate.ratings,
            "probability": response.aggregate.pmf,
        }
    )
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("rating:O", title="Likert Rating"),
            y=alt.Y("probability:Q", title="Probability", axis=alt.Axis(format="%")),
        )
    )
    text = chart.mark_text(
        align="center",
        baseline="bottom",
        dy=-3,  # Nudges text up so it doesn't overlap with the bar
    ).encode(text=alt.Text("probability:Q", format=".1%"))
    return (chart + text).properties(title="Aggregate Likert Distribution")


async def simulate(
    title: str,
    description: str,
    price: str,
    url: str,
    sample_id: str,
    persona_group: str,
    persona_csv_file,
    persona_filters_text: str,
    persona_generations_text: str,
    persona_injections_text: str,
    additional_questions_text: str,
    population_spec_text: str,
    population_spec_file,
    n_per_persona: int,
    total_n: int,
    stratified: bool,
    custom_question: str,
):
    if not description and not url and not sample_id:
        raise gr.Error("Provide either a concept description or a URL.")

    concept_url = coerce_http_url(url)

    concept = ConceptInput(
        title=title or None,
        text=description or None,
        price=price or None,
        url=concept_url,
    )

    options = SimulationOptions(
        n=max(n_per_persona, 1),
        stratified=stratified,
        total_n=total_n or None,
    )

    persona_csv = _read_file(persona_csv_file)
    persona_group_value = (
        persona_group if persona_group and persona_group != "(None)" else None
    )

    persona_filters: List[PersonaFilter] = []
    if persona_filters_text:
        for line in persona_filters_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                persona_filters.append(parse_filter_expression(line))
            except ValueError as exc:  # pragma: no cover - handled via UI feedback
                raise gr.Error(f"Invalid persona filter: {exc}") from exc

    persona_generations: List[PersonaGenerationTask] = []
    if persona_generations_text:
        for line in persona_generations_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                persona_generations.append(parse_generation_expression(line))
            except ValueError as exc:  # pragma: no cover
                raise gr.Error(f"Invalid persona generation: {exc}") from exc

    persona_injections: List[PersonaInjection] = []
    if persona_injections_text:
        stripped = persona_injections_text.strip()
        parsed = False
        if stripped.startswith("["):
            try:
                payloads = json.loads(stripped)
                for entry in payloads:
                    persona_injections.append(
                        parse_injection_payload(json.dumps(entry))
                    )
                parsed = True
            except (ValueError, TypeError) as exc:  # pragma: no cover
                raise gr.Error(f"Invalid persona injection JSON: {exc}") from exc
        if not parsed:
            for line in stripped.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    persona_injections.append(parse_injection_payload(line))
                except ValueError as exc:  # pragma: no cover
                    raise gr.Error(f"Invalid persona injection: {exc}") from exc

    additional_questions: List[str] = []
    if additional_questions_text:
        for line in additional_questions_text.splitlines():
            line = line.strip()
            if line:
                additional_questions.append(line)

    population_spec = None
    spec_text: Optional[str] = None
    if population_spec_file is not None:
        spec_text = _read_file(population_spec_file)
    elif population_spec_text:
        spec_text = population_spec_text

    if spec_text:
        try:
            population_spec = parse_population_spec_input(spec_text)
        except ValueError as exc:  # pragma: no cover
            raise gr.Error(f"Invalid population spec: {exc}") from exc

    request = SimulationRequest(
        concept=concept,
        persona_group=persona_group_value,
        persona_csv=persona_csv,
        persona_filters=persona_filters,
        persona_generations=persona_generations,
        persona_injections=persona_injections,
        population_spec=population_spec,
        questions=additional_questions,
        sample_id=sample_id or None,
        intent_question=custom_question or None,
        options=options,
    )

    response = await run_simulation(request)

    markdown = _make_markdown(response)
    table_rows = _persona_table(response)
    metadata = _metadata(response)
    plot = _plot_distribution(response)

    return markdown, table_rows, metadata, plot


def _load_sample_fields(sample_id: str):
    scenario = load_sample(sample_id)
    persona_value = scenario.persona_group or "(None)"
    question = scenario.intent_question or ""
    return (
        scenario.title,
        scenario.description,
        scenario.price or "",
        scenario.source or "",
        persona_value,
        question,
    )


def launch(
    *,
    server_port: Optional[int] = None,
    server_name: Optional[str] = None,
    share: bool = False,
) -> None:
    persona_options = ["(None)"] + list(PERSONA_LIBRARY.keys())
    sample_options = get_sample_ids()
    default_scenario = default_sample()

    default_title = default_scenario.title if default_scenario else ""
    default_description = default_scenario.description if default_scenario else ""
    default_price = default_scenario.price if default_scenario else ""
    default_url = default_scenario.source if default_scenario else ""
    default_persona_group = "(None)"
    if default_scenario and default_scenario.persona_group in persona_options:
        default_persona_group = default_scenario.persona_group
    default_question = default_scenario.intent_question if default_scenario else ""
    default_sample_id = default_scenario.sample_id if default_scenario else ""

    with gr.Blocks(title="SSR Synthetic Consumer Research") as demo:
        gr.Markdown(
            "## SSR Synthetic Consumer Research\n"
            "Provide a concept and audience to simulate purchase intent "
            "responses using GPT-5 and semantic similarity rating."
        )

        sample_dropdown = gr.Dropdown(
            choices=[(title, sid) for sid, title in sample_options.items()],
            value=default_sample_id,
            label="Sample Scenario",
            info="Select a built-in concept to auto-populate fields.",
        )
        load_sample_button = gr.Button("Load Sample Details")

        with gr.Row():
            title_input = gr.Textbox(
                label="Concept Title",
                placeholder="RadiantSmile Whitening Toothpaste",
                value=default_title,
            )
            price_input = gr.Textbox(
                label="Price",
                placeholder="$5.99",
                value=default_price,
            )

        description_input = gr.Textbox(
            label="Concept Description",
            placeholder="Describe the concept or paste copy shown to consumers",
            lines=6,
            value=default_description,
        )

        url_input = gr.Textbox(label="Concept URL (optional)", value=default_url)

        with gr.Row():
            persona_group_input = gr.Dropdown(
                choices=persona_options,
                value=default_persona_group,
                label="Persona Library Group",
                info="Choose a pre-weighted segment or leave empty.",
            )
            persona_csv_input = gr.File(
                label="Upload Persona CSV",
                file_types=[".csv"],
                type="binary",
            )

        with gr.Accordion("Advanced Persona Controls", open=False):
            gr.Markdown(
                "Configure dynamic personas. Enter one expression per line."
            )
            persona_filter_input = gr.Textbox(
                label="Persona Filters",
                lines=3,
                placeholder=(
                    "Example: group=us_toothpaste_buyers;include.age=25-44;"
                    "keyword=family;share=0.5"
                ),
            )
            persona_generation_input = gr.Textbox(
                label="Persona Generation Prompts",
                lines=3,
                placeholder=(
                    "Example: prompt=Eco parents;count=2;share=0.3;attr.region=US"
                ),
            )
            persona_injection_input = gr.Textbox(
                label="Persona Injections",
                lines=3,
                placeholder=(
                    "Example: name=Custom Segment;descriptors=loyal,premium;share=0.2"
                ),
            )
            additional_questions_input = gr.Textbox(
                label="Additional Questions",
                lines=3,
                placeholder="One question per line (defaults always include primary intent question)",
            )
            population_spec_input = gr.Textbox(
                label="Population Spec (YAML/JSON)",
                lines=4,
                placeholder="Paste full spec to control base groups, marginals, and raking",
            )
            population_spec_file = gr.File(
                label="Upload Population Spec",
                file_types=[".yml", ".yaml", ".json"],
                type="binary",
            )

        with gr.Row():
            n_input = gr.Slider(
                label="Samples per Persona",
                minimum=1,
                maximum=200,
                step=1,
                value=50,
            )
            total_input = gr.Slider(
                label="Total Samples (overrides per persona when > 0)",
                minimum=0,
                maximum=1000,
                step=10,
                value=0,
            )
            stratified_input = gr.Checkbox(label="Stratified Allocation", value=True)

        question_input = gr.Textbox(
            label="Custom Intent Question (optional)",
            placeholder="How likely would you be to purchase this product?",
            value=default_question,
        )

        run_button = gr.Button("Run Simulation")

        output_markdown = gr.Markdown()
        output_plot = gr.Plot()
        persona_table = gr.Dataframe(
            headers=[
                "Persona",
                "Weight",
                "Age",
                "Region",
                "Income",
                "Sample N",
                "Mean",
                "Top2",
                "Themes",
            ],
            datatype=[
                "str",
                "number",
                "str",
                "str",
                "str",
                "number",
                "number",
                "number",
                "str",
            ],
            interactive=False,
        )
        metadata_json = gr.JSON(label="Metadata")

        run_button.click(
            simulate,
            inputs=[
                title_input,
                description_input,
                price_input,
                url_input,
                sample_dropdown,
                persona_group_input,
                persona_csv_input,
                persona_filter_input,
                persona_generation_input,
                persona_injection_input,
                additional_questions_input,
                population_spec_input,
                population_spec_file,
                n_input,
                total_input,
                stratified_input,
                question_input,
            ],
            outputs=[output_markdown, persona_table, metadata_json, output_plot],
        )

        load_sample_button.click(
            _load_sample_fields,
            inputs=[sample_dropdown],
            outputs=[
                title_input,
                description_input,
                price_input,
                url_input,
                persona_group_input,
                question_input,
            ],
        )

    launch_kwargs: Dict[str, Any] = {}
    if server_port is not None:
        launch_kwargs["server_port"] = server_port
    if server_name is not None:
        launch_kwargs["server_name"] = server_name
    if share:
        launch_kwargs["share"] = share

    demo.launch(**launch_kwargs)


__all__ = ["launch"]
