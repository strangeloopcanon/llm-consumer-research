"""Perplexity implementation of LLMProvider."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from ..cache import add_to_cache, get_from_cache
from ..config import get_settings
from ..models import PersonaSpec
from .base import LLMProvider, LLMResponse


class PerplexityProvider(LLMProvider):
    """Perplexity provider implementation (using OpenAI-compatible API)."""

    def __init__(self, model_override: Optional[str] = None) -> None:
        settings = get_settings()
        api_key = settings.perplexity_api_key
        if not api_key:
            raise RuntimeError("PERPLEXITY_API_KEY is not configured")

        self._client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.perplexity.ai"
        )
        self._model = model_override or settings.perplexity_model

    @property
    def provider_name(self) -> str:
        return "perplexity"

    @property
    def default_model(self) -> str:
        return self._model

    async def generate_rationale(
        self,
        persona: PersonaSpec,
        prompt_block: str,
        question: str,
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
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
        )

        if seed is not None:
            prompt += f"Response ID: {seed}\n"

        prompt += "Return only the JSON object."

        cached_response = get_from_cache(prompt)
        if cached_response:
            return LLMResponse(
                rationale=cached_response,
                provider=self.provider_name,
                model="cached",
            )

        # Perplexity doesn't strictly support response_format={"type": "json_object"} on all models
        # but we can try or just parse the text.
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature or 0.1,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise RuntimeError("Model returned empty rationale")

        import json

        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end != 0:
            json_str = raw_text[start:end]
            try:
                parsed = json.loads(json_str)
                rationale = parsed.get("rationale") or raw_text
            except json.JSONDecodeError:
                rationale = raw_text
        else:
            rationale = raw_text

        add_to_cache(prompt, rationale)
        return LLMResponse(
            rationale=rationale,
            provider=self.provider_name,
            model=self._model,
            raw_response=response,
        )
