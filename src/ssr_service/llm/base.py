"""Base interface for LLM providers."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Optional

from ..models import PersonaSpec


@dataclass(slots=True)
class LLMResponse:
    """Standardized response from an LLM provider."""
    
    rationale: str
    provider: str
    model: str
    raw_response: Any = None


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    async def generate_rationale(
        self,
        persona: PersonaSpec,
        prompt_block: str,
        question: str,
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Generate a rationale for a given persona and concept."""
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass
