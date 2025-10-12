"""Concept ingestion utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .models import ConceptInput


@dataclass(slots=True)
class ConceptArtifact:
    """Structured concept content for prompting."""

    title: Optional[str]
    description: str
    price: Optional[str]
    url: Optional[str]

    def as_prompt_block(self) -> str:
        parts = []
        if self.title:
            parts.append(f"Product: {self.title}")
        if self.price:
            parts.append(f"Price: {self.price}")
        parts.append(self.description.strip())
        if self.url:
            parts.append(f"Source: {self.url}")
        return "\n".join(parts)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def fetch_url_text(url: str) -> tuple[Optional[str], str]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string.strip() if soup.title else None

    article = " ".join(
        p.get_text(separator=" ", strip=True)
        for p in soup.find_all(["p", "li"])[:20]
    )
    description = _clean_text(article)[:2000]
    return title, description


async def ingest_concept(concept: ConceptInput) -> ConceptArtifact:
    title = concept.title
    price = concept.price
    description = concept.text or ""

    if concept.url:
        fetched_title, fetched_desc = await fetch_url_text(str(concept.url))
        title = title or fetched_title
        if not description:
            description = fetched_desc

    if not description:
        raise ValueError("Concept description could not be determined")

    return ConceptArtifact(
        title=title,
        description=description,
        price=price,
        url=str(concept.url) if concept.url else None,
    )


__all__ = ["ConceptArtifact", "ingest_concept"]
