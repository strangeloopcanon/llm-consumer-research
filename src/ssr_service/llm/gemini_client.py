"""Gemini implementation of LLMProvider."""

from __future__ import annotations

from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmBlockThreshold, HarmCategory

from ..cache import add_to_cache, get_from_cache
from ..config import get_settings
from ..models import PersonaSpec
from .base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Gemini provider implementation."""

    def __init__(self, model_override: Optional[str] = None) -> None:
        settings = get_settings()
        api_key = settings.google_api_key
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        genai.configure(api_key=api_key)
        self._model_name = model_override or settings.gemini_model
        self._model = genai.GenerativeModel(self._model_name)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._model_name

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
        cache_namespace = f"{self.provider_name}:{self._model_name}"

        cached_response = get_from_cache(prompt, namespace=cache_namespace)
        if cached_response:
            return LLMResponse(
                rationale=cached_response,
                provider=self.provider_name,
                model="cached",
            )

        # Run in executor since Gemini SDK is synchronous for now (or check for async support)
        # The current google-generativeai SDK has async methods in beta or via specific clients,
        # but standard generate_content is sync. We'll use generate_content_async if available,
        # or wrap it.
        
        response = await self._model.generate_content_async(
            contents=prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=temperature,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        raw_text = response.text
        if not raw_text:
            raise RuntimeError("Model returned empty rationale")

        import json

        try:
            parsed = json.loads(raw_text)
            rationale = parsed.get("rationale") or raw_text
        except json.JSONDecodeError:
            rationale = raw_text

        add_to_cache(prompt, rationale, namespace=cache_namespace)
        return LLMResponse(
            rationale=rationale,
            provider=self.provider_name,
            model=self._model_name,
            raw_response=response,
        )
