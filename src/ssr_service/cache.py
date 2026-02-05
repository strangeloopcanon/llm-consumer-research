"""In-memory cache for LLM API calls."""

from __future__ import annotations

import hashlib
from typing import Dict, Optional

_CACHE: Dict[str, str] = {}


def get_from_cache(prompt: str, *, namespace: str = "") -> Optional[str]:
    """Get a response from the cache."""
    key = _get_key(prompt, namespace=namespace)
    return _CACHE.get(key)


def add_to_cache(prompt: str, response: str, *, namespace: str = "") -> None:
    """Add a response to the cache."""
    key = _get_key(prompt, namespace=namespace)
    _CACHE[key] = response


def _get_key(prompt: str, *, namespace: str = "") -> str:
    """Get the cache key for a prompt."""
    payload = f"{namespace}\n{prompt}" if namespace else prompt
    return hashlib.sha256(payload.encode()).hexdigest()
