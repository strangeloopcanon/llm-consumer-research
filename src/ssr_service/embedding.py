"""Embedding utilities."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

import numpy as np
from openai import OpenAI

from .config import get_settings


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    base_url = str(settings.openai_base_url) if settings.openai_base_url else None
    return OpenAI(api_key=settings.openai_api_key, base_url=base_url)


def embed_texts(texts: Iterable[str]) -> np.ndarray:
    """Embed a sequence of texts using the configured embedding model."""

    texts_list: List[str] = list(texts)
    if not texts_list:
        return np.empty((0,))

    settings = get_settings()
    client = _get_client()

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts_list,
    )

    vectors = [np.array(item.embedding, dtype=np.float32) for item in response.data]
    return np.vstack(vectors)


def embed_text(text: str) -> np.ndarray:
    """Embed a single text and return a 1D vector."""

    return embed_texts([text])[0]


__all__ = ["embed_text", "embed_texts"]
