"""Persona generation backends for dynamic audience slices."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List

from openai import AsyncOpenAI

from .config import AppSettings
from .models import PersonaGenerationTask, PersonaSpec


def _extract_keywords(text: str, limit: int = 6) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-']{2,}", text.lower())
    deduped: List[str] = []
    for word in words:
        if word in deduped:
            continue
        deduped.append(word)
    return deduped[:limit]


def _fallback_name(prompt: str, index: int) -> str:
    base = prompt.strip() or "Generated Persona"
    base = re.sub(r"[^A-Za-z0-9 ]+", "", base).strip()
    base = base.title()[:40] or "Generated Persona"
    return f"{base} #{index + 1}"


def _split_values(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    return [item.strip() for item in re.split(r"[;,]", text) if item.strip()]


def _apply_attributes(persona: PersonaSpec, attributes: Dict[str, object]) -> None:
    for field, raw_value in attributes.items():
        if not hasattr(persona, field):
            continue
        value_list = _split_values(raw_value)
        current = getattr(persona, field, None)
        if isinstance(current, list):
            if value_list:
                merged = list(dict.fromkeys(current + value_list))
                setattr(persona, field, merged)
        else:
            if value_list:
                setattr(persona, field, value_list[0])
            elif isinstance(raw_value, str):
                setattr(persona, field, raw_value)


AGE_KEYWORDS = {
    "18-24": {"gen z", "student", "campus", "college", "youth", "teen"},
    "25-44": {"millennial", "parent", "young professional", "career"},
    "45-64": {"midlife", "caregiver", "manager", "established"},
    "65+": {"senior", "retiree", "older", "caregiver"},
}


def _infer_age(descriptors: Iterable[str]) -> str | None:
    lowered = {desc.lower() for desc in descriptors}
    for age_band, keywords in AGE_KEYWORDS.items():
        if lowered & keywords:
            return age_band
    return None


class PersonaGenerator:
    async def generate(self, task: PersonaGenerationTask) -> List[PersonaSpec]:
        raise NotImplementedError


class HeuristicPersonaGenerator(PersonaGenerator):
    async def generate(self, task: PersonaGenerationTask) -> List[PersonaSpec]:
        descriptors = _extract_keywords(task.prompt)
        personas: List[PersonaSpec] = []

        for idx, template in enumerate(task.templates):
            fallback_name = _fallback_name(task.prompt, idx)
            persona = template.to_persona_spec(fallback_name=fallback_name)
            if not persona.descriptors and descriptors:
                persona.descriptors = descriptors[:3]
            if not persona.motivations and descriptors:
                persona.motivations = [
                    f"Seeks better {descriptors[0]} solutions",
                    f"Values {descriptors[0]}-driven benefits",
                ][:2]
            if not persona.pain_points and descriptors:
                persona.pain_points = [
                    f"Frustrated by limited {descriptors[0]} options"
                ]
            inferred_age = _infer_age(persona.descriptors)
            if inferred_age and not persona.age:
                persona.age = inferred_age
            _apply_attributes(persona, task.attributes)
            personas.append(persona)

        remaining = max(task.count - len(personas), 0)
        fallback_descriptor = descriptors[0] if descriptors else task.prompt or "audience"
        for i in range(remaining):
            name = _fallback_name(task.prompt, len(personas))
            persona_data = {
                "name": name,
                "descriptors": descriptors[:3] or [fallback_descriptor],
                "habits": [
                    f"Engages with {fallback_descriptor} content weekly",
                    f"Researches {fallback_descriptor} recommendations online",
                ][:2],
                "motivations": [
                    f"Wants trustworthy {fallback_descriptor} solutions",
                    f"Cares about authentic {fallback_descriptor} experiences",
                ][:2],
                "pain_points": [
                    f"Overwhelmed by inconsistent {fallback_descriptor} messaging"
                ],
                "preferred_channels": [
                    "social media",
                    "word of mouth",
                    "email",
                ][:2],
                "weight": 1.0,
            }
            inferred_age = _infer_age(descriptors)
            if inferred_age:
                persona_data["age"] = inferred_age
            persona = PersonaSpec.model_validate(persona_data)
            _apply_attributes(persona, task.attributes)
            personas.append(persona)

        if not personas:
            personas.append(
                PersonaSpec(
                    name=_fallback_name(task.prompt, 0),
                    descriptors=[fallback_descriptor],
                    weight=1.0,
                )
            )

        return personas[: task.count]


@dataclass
class OpenAIConfig:
    client: AsyncOpenAI
    model: str


def _build_generator_prompt(task: PersonaGenerationTask) -> str:
    template_snippets = []
    for template in task.templates:
        template_snippets.append(
            {
                "name": template.name or "",
                "age": template.age or "",
                "region": template.region or "",
                "descriptors": template.descriptors,
                "habits": template.habits,
                "motivations": template.motivations,
                "pain_points": template.pain_points,
                "preferred_channels": template.preferred_channels,
                "weight": template.weight,
            }
        )
    payload = {
        "prompt": task.prompt,
        "count": task.count,
        "templates": template_snippets,
        "attributes": task.attributes,
    }
    return (
        "Synthesize realistic consumer personas for the described audience. "
        "Return a JSON array where each persona is an object with keys "
        'name, age, gender, income, region, occupation, education, household, '
        "purchase_frequency, usage_context, background, habits, motivations, "
        "pain_points, preferred_channels, descriptors, notes, source, weight. "
        "Weights should be proportional but do not need to sum to one. "
        "Use the provided prompt, attribute hints, and optional templates. "
        "Ensure the output is valid JSON only. Input context:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


class OpenAIPersonaGenerator(PersonaGenerator):
    def __init__(self, config: OpenAIConfig):
        self._client = config.client
        self._model = config.model

    async def generate(self, task: PersonaGenerationTask) -> List[PersonaSpec]:
        prompt = _build_generator_prompt(task)
        response = await self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": "You are a senior insights researcher crafting richly detailed personas.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        text = (response.output_text or "").strip()
        if not text:
            raise RuntimeError("Model returned empty persona payload")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - depends on API
            raise RuntimeError("Persona generator returned non-JSON output") from exc

        if not isinstance(data, list):
            raise RuntimeError("Persona generator must return a JSON array of personas")

        personas: List[PersonaSpec] = []
        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                continue
            entry.setdefault("name", _fallback_name(task.prompt, idx))
            entry.setdefault("weight", entry.get("weight") or 1.0)
            persona = PersonaSpec.model_validate(entry)
            _apply_attributes(persona, task.attributes)
            personas.append(persona)

        if not personas:
            raise RuntimeError("Persona generator produced no usable personas")

        return personas[: task.count]


def _openai_config(settings: AppSettings) -> OpenAIConfig:
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured for persona generation")
    base_url = str(settings.openai_base_url) if settings.openai_base_url else None
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return OpenAIConfig(client=client, model=settings.openai_responses_model)


async def synthesize_personas(
    task: PersonaGenerationTask, settings: AppSettings
) -> List[PersonaSpec]:
    """Generate personas using the requested strategy with heuristic fallback."""

    generator: PersonaGenerator
    if task.strategy == "openai":
        try:
            generator = OpenAIPersonaGenerator(_openai_config(settings))
            personas = await generator.generate(task)
        except Exception:
            heuristic = HeuristicPersonaGenerator()
            personas = await heuristic.generate(task)
    else:
        heuristic = HeuristicPersonaGenerator()
        personas = await heuristic.generate(task)

    if not personas:
        personas = await HeuristicPersonaGenerator().generate(
            task.model_copy(update={"strategy": "heuristic"})
        )

    return personas[: task.count]


__all__ = ["synthesize_personas", "HeuristicPersonaGenerator", "OpenAIPersonaGenerator"]
