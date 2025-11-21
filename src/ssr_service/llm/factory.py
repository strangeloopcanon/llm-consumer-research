"""Factory for creating LLM providers."""

from __future__ import annotations

from typing import Optional

from .base import LLMProvider
from .openai_client import OpenAIProvider
from .anthropic_client import AnthropicProvider
from .gemini_client import GeminiProvider
from .perplexity_client import PerplexityProvider


def get_provider(name: str, model_override: Optional[str] = None) -> LLMProvider:
    """Get an LLM provider by name."""
    name = name.lower()
    if name == "openai":
        return OpenAIProvider(model_override)
    elif name == "anthropic" or name == "claude":
        return AnthropicProvider(model_override)
    elif name == "gemini" or name == "google":
        return GeminiProvider(model_override)
    elif name == "perplexity":
        return PerplexityProvider(model_override)
    else:
        raise ValueError(f"Unknown provider: {name}")
