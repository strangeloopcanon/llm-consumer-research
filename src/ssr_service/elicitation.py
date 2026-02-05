"""LLM elicitation client using Responses API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI

from .config import get_settings
from .models import PersonaSpec


@dataclass(slots=True)
class ElicitationResult:
    rationale: str
    used_model: str


class ElicitationClient:
    """Generate concise rationales from persona prompts."""

    def __init__(self, model_override: Optional[str] = None) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        base_url = str(settings.openai_base_url) if settings.openai_base_url else None
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model_override or settings.openai_responses_model

    async def generate_rationale(
        self,
        persona: PersonaSpec,
        prompt_block: str,
        question: str,
    ) -> ElicitationResult:
        persona_description = persona.describe()

        prompt = (
            "You are roleplaying as a consumer in a concept test."
            " Answer concisely in 1-2 sentences. Be realistic and grounded."
            " Avoid numerical ratings or Likert numbers."
            " Always respond with valid JSON of the form {\"rationale\": \"...\"}."
            "\n\n"
            f"Persona: {persona.name} ({persona_description}).\n"
            f"Stimulus:\n{prompt_block}\n\n"
            f"Question: {question}\n"
            "Return only the JSON object."
        )
        cache_namespace = f"elicitation:{self._model}"

        from .cache import add_to_cache, get_from_cache

        cached_response = get_from_cache(prompt, namespace=cache_namespace)
        if cached_response:
            return ElicitationResult(rationale=cached_response, used_model="cached")

        response = await self._client.responses.create(
            model=self._model,
            input=prompt,
        )

        raw_text = response.output_text
        if not raw_text:
            raise RuntimeError("Model returned empty rationale")

        raw_text = raw_text.strip()

        rationale = raw_text
        if raw_text.startswith("{"):
            import json

            try:
                parsed = json.loads(raw_text)
                rationale = parsed.get("rationale") or raw_text
            except json.JSONDecodeError:
                rationale = raw_text

        add_to_cache(prompt, rationale, namespace=cache_namespace)
        return ElicitationResult(rationale=rationale, used_model=response.model)


async def generate_batch(
    client: ElicitationClient,
    persona: PersonaSpec,
    prompt_block: str,
    question: str,
    n: int,
    concurrency: int = 32,
) -> list[ElicitationResult]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[ElicitationResult] = []

    async def run_single(idx: int) -> None:
        async with semaphore:
            try:
                res = await client.generate_rationale(
                    persona=persona,
                    prompt_block=prompt_block,
                    question=question,
                )
                results.append(res)
            except Exception as err:  # noqa: BLE001
                # One retry in case of transient API issues
                try:
                    res = await client.generate_rationale(
                        persona=persona,
                        prompt_block=prompt_block,
                        question=question,
                    )
                    results.append(res)
                except Exception as inner_err:  # noqa: BLE001
                    raise RuntimeError(
                        "Failed to elicit rationale for persona "
                        f"{persona.name}: {inner_err}"
                    ) from err

    await asyncio.gather(*(run_single(i) for i in range(n)))
    return results


__all__ = ["ElicitationClient", "ElicitationResult", "generate_batch"]
