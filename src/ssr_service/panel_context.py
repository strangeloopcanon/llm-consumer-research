"""Panel context chunking and allocation helpers."""

from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Iterable, List, Sequence

from .models import PanelContextSpec, PersonaSpec

_BULLET_PREFIX_RE = re.compile(r"^([-*•]|\d+[.)])\s+")


def _dedupe_chunks(chunks: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for chunk in chunks:
        text = re.sub(r"\s+", " ", str(chunk)).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _try_parse_json_list(text: str) -> List[str]:
    candidate = text.strip()
    if not candidate or not candidate.startswith("["):
        return []
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return _dedupe_chunks(str(item) for item in data)


def chunk_context_text(text: str) -> List[str]:
    """Split free-form text into stable, human-sized context chunks."""

    candidate = text.strip()
    if not candidate:
        return []

    parsed = _try_parse_json_list(candidate)
    if parsed:
        return parsed

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", candidate) if p.strip()]
    if len(paragraphs) > 1:
        return _dedupe_chunks(paragraphs)

    lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    if any(_BULLET_PREFIX_RE.match(line) for line in lines):
        return _dedupe_chunks(_BULLET_PREFIX_RE.sub("", line).strip() for line in lines)

    if ";" in candidate:
        return _dedupe_chunks(part for part in candidate.split(";"))

    return _dedupe_chunks([candidate])


def panel_context_chunks(spec: PanelContextSpec | None) -> List[str]:
    if spec is None:
        return []
    chunks: List[str] = []
    chunks.extend(spec.chunks)
    if spec.text:
        chunks.extend(chunk_context_text(spec.text))
    return _dedupe_chunks(chunks)


def _stable_seed(value: str) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)


def apply_panel_context(
    personas: Sequence[PersonaSpec],
    spec: PanelContextSpec,
    *,
    seed: int,
) -> int:
    """Mutate personas in-place by appending allocated context chunks.

    Returns the number of context chunks available for allocation.
    """

    chunks = panel_context_chunks(spec)
    if not chunks or spec.chunks_per_persona <= 0:
        return len(chunks)

    per_persona = spec.chunks_per_persona

    if spec.mode == "shared":
        assigned = chunks[:per_persona]
        for persona in personas:
            persona.context = _dedupe_chunks([*persona.context, *assigned])
        return len(chunks)

    if spec.mode == "round_robin":
        cursor = 0
        for persona in personas:
            picks = [chunks[(cursor + idx) % len(chunks)] for idx in range(per_persona)]
            cursor += per_persona
            persona.context = _dedupe_chunks([*persona.context, *picks])
        return len(chunks)

    for idx, persona in enumerate(personas):
        rng = random.Random(_stable_seed(f"{seed}|{idx}|{persona.name}"))  # nosec B311
        if len(chunks) <= per_persona:
            picks = chunks
        else:
            picks = rng.sample(chunks, k=per_persona)
        persona.context = _dedupe_chunks([*persona.context, *picks])

    return len(chunks)


__all__ = ["apply_panel_context", "chunk_context_text", "panel_context_chunks"]
