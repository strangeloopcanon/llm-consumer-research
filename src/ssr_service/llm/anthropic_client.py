"""Anthropic implementation of LLMProvider."""

from __future__ import annotations

from typing import Optional

from anthropic import AsyncAnthropic

from ..cache import add_to_cache, get_from_cache
from ..config import get_settings
from ..models import PersonaSpec
from .base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation."""

    def __init__(self, model_override: Optional[str] = None) -> None:
        settings = get_settings()
        api_key = settings.anthropic_api_key
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model_override or settings.anthropic_model

    @property
    def provider_name(self) -> str:
        return "anthropic"

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

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature or 1.0,
        )

        raw_text = response.content[0].text
        if not raw_text:
            raise RuntimeError("Model returned empty rationale")

        import json

        # Anthropic might include preambles, so we try to find the JSON
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
