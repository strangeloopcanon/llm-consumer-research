"""Tests for cache namespacing behavior."""

from __future__ import annotations

from ssr_service import cache


def test_cache_isolated_by_namespace() -> None:
    cache._CACHE.clear()

    prompt = "same prompt"
    cache.add_to_cache(prompt, "openai-response", namespace="openai:gpt-5")
    cache.add_to_cache(prompt, "anthropic-response", namespace="anthropic:claude")

    assert (
        cache.get_from_cache(prompt, namespace="openai:gpt-5") == "openai-response"
    )
    assert (
        cache.get_from_cache(prompt, namespace="anthropic:claude")
        == "anthropic-response"
    )
    assert cache.get_from_cache(prompt, namespace="gemini:1.5") is None
