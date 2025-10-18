"""Cache for OpenAI API calls."""

from __future__ import annotations

import hashlib
from typing import Dict, Optional

_CACHE: Dict[str, str] = {}


def get_from_cache(prompt: str) -> Optional[str]:
    """Get a response from the cache."""
    key = _get_key(prompt)
    return _CACHE.get(key)


def add_to_cache(prompt: str, response: str) -> None:
    """Add a response to the cache."""
    key = _get_key(prompt)
    _CACHE[key] = response


def _get_key(prompt: str) -> str:
    """Get the cache key for a prompt."""
    return hashlib.sha256(prompt.encode()).hexdigest()
