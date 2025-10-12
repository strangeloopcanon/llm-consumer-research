"""Gradio frontend for running simulations interactively."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import gradio as gr

from .config import get_settings
from .models import ConceptInput, SimulationOptions, SimulationRequest
from .orchestrator import run_simulation
from .personas import load_library
from .sample_data import get_sample_ids, load_sample, default_sample


SETTINGS = get_settings()
PERSONA_LIBRARY = load_library(Path(SETTINGS.persona_library_path))


def _read_file(file_obj) -> Optional[str]:  # type: ignore[no-untyped-def]
    if file_obj is None:
        return None
    content = file_obj.read()
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return str(content)


def _make_markdown(response) -> str:
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
        md_lines.append(f"**{persona.name}** (weight: {persona.weight:.0%}, n={dist.sample_n})")
        md_lines.append(
            f"- Mean: {dist.mean:.2f}, Top-2: {dist.top2box:.2%}, Themes: {', '.join(persona_result.themes) or 'n/a'}"
        )
        bullets = persona_result.rationales[:2]
        if bullets:
            md_lines.append("  - " + bullets[0])
            if len(bullets) > 1:
                md_lines.append("  - " + bullets[1])
        md_lines.append("")

    return "\n".join(md_lines)


def _persona_table(response) -> List[List[Any]]:
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


def _metadata(response) -> Dict[str, str]:
    return response.metadata


def simulate(
    title: str,
    description: str,
    price: str,
    url: str,
    sample_id: str,
    persona_group: str,
    persona_csv_file,
    n_per_persona: int,
    total_n: int,
    stratified: bool,
    custom_question: str,
):
    if not description and not url and not sample_id:
        raise gr.Error("Provide either a concept description or a URL.")

    concept = ConceptInput(
        title=title or None,
        text=description or None,
        price=price or None,
        url=url or None,
    )

    options = SimulationOptions(
        n=max(n_per_persona, 1),
        stratified=stratified,
        total_n=total_n or None,
    )

    persona_csv = _read_file(persona_csv_file)
    persona_group_value = persona_group if persona_group and persona_group != "(None)" else None

    request = SimulationRequest(
        concept=concept,
        persona_group=persona_group_value,
        persona_csv=persona_csv,
        sample_id=sample_id or None,
        intent_question=custom_question or None,
        options=options,
    )

    response = asyncio.run(run_simulation(request))

    markdown = _make_markdown(response)
    table_rows = _persona_table(response)
    metadata = _metadata(response)

    return markdown, table_rows, metadata


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


def launch() -> None:
    persona_options = ["(None)"] + list(PERSONA_LIBRARY.keys())
    sample_options = get_sample_ids()
    default_scenario = default_sample()

    default_title = default_scenario.title if default_scenario else ""
    default_description = default_scenario.description if default_scenario else ""
    default_price = default_scenario.price if default_scenario else ""
    default_url = default_scenario.source if default_scenario else ""
    default_persona_group = (
        default_scenario.persona_group if default_scenario and default_scenario.persona_group in persona_options else "(None)"
    )
    default_question = default_scenario.intent_question if default_scenario else ""
    default_sample_id = default_scenario.sample_id if default_scenario else ""

    with gr.Blocks(title="SSR Synthetic Consumer Research") as demo:
        gr.Markdown("""## SSR Synthetic Consumer Research\nProvide a concept and audience to simulate purchase intent responses using GPT-5 and semantic similarity rating.""")

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
            datatype=["str", "number", "str", "str", "str", "number", "number", "number", "str"],
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
                n_input,
                total_input,
                stratified_input,
                question_input,
            ],
            outputs=[output_markdown, persona_table, metadata_json],
        )

        load_sample_button.click(
            _load_sample_fields,
            inputs=[sample_dropdown],
            outputs=[title_input, description_input, price_input, url_input, persona_group_input, question_input],
        )

    demo.launch()


__all__ = ["launch"]
