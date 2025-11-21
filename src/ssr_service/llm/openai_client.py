"""OpenAI implementation of LLMProvider."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from ..cache import add_to_cache, get_from_cache
from ..config import get_settings
from ..models import PersonaSpec
from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, model_override: Optional[str] = None) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        base_url = str(settings.openai_base_url) if settings.openai_base_url else None
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model_override or settings.openai_responses_model

    @property
    def provider_name(self) -> str:
        return "openai"

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

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise RuntimeError("Model returned empty rationale")

        import json

        try:
            parsed = json.loads(raw_text)
            rationale = parsed.get("rationale") or raw_text
        except json.JSONDecodeError:
            rationale = raw_text

        add_to_cache(prompt, rationale)
        return LLMResponse(
            rationale=rationale,
            provider=self.provider_name,
            model=self._model,
            raw_response=response,
        )
