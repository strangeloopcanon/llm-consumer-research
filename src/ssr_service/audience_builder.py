"""Audience Builder Agent: Parse heterogeneous evidence and synthesize representative panels.

This module provides:
1. A multi-format parser that extracts text summaries from CSV, PDF, JSON, and text files.
2. A synthesis agent that uses an LLM to generate a PopulationSpec from evidence.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .config import AppSettings, get_settings
from .models import (
    PersonaInjection,
    PersonaSpec,
    PopulationSpec,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Multi-Format Parser
# ============================================================================


def _summarize_csv(content: str, filename: str, max_rows: int = 50) -> str:
    """Parse CSV content and return a text summary."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)[:max_rows]
        if not rows:
            return f"[{filename}] Empty CSV file."

        columns = list(rows[0].keys())
        summary_parts = [
            f"[{filename}] CSV with {len(rows)} rows (showing up to {max_rows}).",
            f"Columns: {', '.join(columns)}",
        ]

        # Provide a sample of unique values per column
        for col in columns[:10]:  # Limit to first 10 columns
            values = list({row.get(col, "") for row in rows if row.get(col)})[:10]
            if values:
                summary_parts.append(f"  - {col}: {', '.join(str(v) for v in values)}")

        return "\n".join(summary_parts)
    except Exception as e:  # noqa: BLE001
        return f"[{filename}] Failed to parse CSV: {e}"


def _summarize_json(content: str, filename: str) -> str:
    """Parse JSON content and return a text summary."""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            sample = data[:10]
            return f"[{filename}] JSON array with {len(data)} items. Sample:\n{json.dumps(sample, indent=2)}"
        elif isinstance(data, dict):
            keys = list(data.keys())[:20]
            return f"[{filename}] JSON object with keys: {', '.join(keys)}"
        else:
            return f"[{filename}] JSON primitive: {data}"
    except Exception as e:  # noqa: BLE001
        return f"[{filename}] Failed to parse JSON: {e}"


def _summarize_text(content: str, filename: str, max_chars: int = 5000) -> str:
    """Return text content, truncated if too long."""
    if len(content) > max_chars:
        return f"[{filename}] Text (truncated to {max_chars} chars):\n{content[:max_chars]}..."
    return f"[{filename}] Text:\n{content}"


def _summarize_pdf(content: bytes, filename: str) -> str:
    """Extract text from PDF bytes. Requires pdfplumber or falls back gracefully."""
    try:
        pdfplumber = importlib.import_module("pdfplumber")
        open_pdf = getattr(pdfplumber, "open", None)
        if open_pdf is None:  # pragma: no cover - runtime guard
            raise ImportError("pdfplumber.open is unavailable")

        with open_pdf(io.BytesIO(content)) as pdf:
            text_parts = []
            for i, page in enumerate(pdf.pages[:10]):  # Limit to first 10 pages
                page_text = page.extract_text() or ""
                text_parts.append(f"[Page {i + 1}]\n{page_text}")
            combined = "\n\n".join(text_parts)
            if len(combined) > 8000:
                combined = combined[:8000] + "..."
            return f"[{filename}] PDF content:\n{combined}"
    except ImportError:
        return f"[{filename}] PDF parsing requires pdfplumber. Install with: pip install pdfplumber"
    except Exception as e:  # noqa: BLE001
        return f"[{filename}] Failed to parse PDF: {e}"


def parse_evidence(
    files: List[Tuple[str, bytes | str]],
) -> str:
    """Parse a list of evidence files and return a combined text summary.

    Args:
        files: List of (filename, content) tuples. Content can be bytes (for PDF)
               or str (for text-based formats).

    Returns:
        A combined text summary of all parsed files.
    """
    summaries = []
    for filename, content in files:
        ext = Path(filename).suffix.lower()

        if ext == ".csv":
            text_content = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
            summaries.append(_summarize_csv(text_content, filename))
        elif ext == ".json":
            text_content = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
            summaries.append(_summarize_json(text_content, filename))
        elif ext == ".pdf":
            byte_content = content if isinstance(content, bytes) else content.encode("utf-8")
            summaries.append(_summarize_pdf(byte_content, filename))
        else:
            # Treat as plain text
            text_content = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
            summaries.append(_summarize_text(text_content, filename))

    return "\n\n---\n\n".join(summaries)


# ============================================================================
# Synthesis Agent
# ============================================================================

SYNTHESIS_SYSTEM_PROMPT = """You are an expert market researcher. Your task is to analyze evidence about a target audience and define a representative panel of 4-8 synthetic personas.

For each persona, you must provide:
- name: A descriptive name for the segment (e.g., "Budget-Conscious Student")
- age: An age range (e.g., "25-34")
- gender: male, female, or non-binary
- region: Geographic region (e.g., "US", "Urban California")
- income: Income bracket (e.g., "Low", "Middle", "Upper middle")
- occupation: Job or life stage (e.g., "Software Engineer", "Stay-at-home parent")
- descriptors: A list of 3-5 behavioral/psychographic traits
- weight: The proportion this segment represents in the target population (all weights should sum to 1.0)

Your output MUST be a valid JSON object with this exact structure:
{
  "injections": [
    {
      "persona": {
        "name": "...",
        "age": "...",
        "gender": "...",
        "region": "...",
        "income": "...",
        "occupation": "...",
        "descriptors": ["...", "..."],
        "weight": 0.25
      },
      "weight_share": 0.25
    }
  ],
  "reasoning": "A brief explanation of how you derived these segments from the evidence."
}

Rules:
1. Base your personas on the evidence provided. Do not invent demographics not supported by the data.
2. Ensure diversity in the personas to cover the range of the target audience.
3. Weights should be proportional to representation in the evidence.
4. If evidence is sparse, make reasonable assumptions but note them in the reasoning.
"""


async def synthesize_panel(
    evidence_summary: str,
    target_description: Optional[str] = None,
    settings: Optional[AppSettings] = None,
) -> Tuple[PopulationSpec, str]:
    """Synthesize a PopulationSpec from evidence using an LLM.

    Args:
        evidence_summary: Text summary from parse_evidence().
        target_description: Optional user-provided description of the target audience.
        settings: App settings (uses default if not provided).

    Returns:
        A tuple of (PopulationSpec, reasoning_text).
    """
    if settings is None:
        settings = get_settings()

    user_prompt_parts = []
    if target_description:
        user_prompt_parts.append(f"Target Audience Description:\n{target_description}")
    user_prompt_parts.append(f"Evidence:\n{evidence_summary}")

    user_prompt = "\n\n".join(user_prompt_parts)

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for audience synthesis")

    base_url = str(settings.openai_base_url) if settings.openai_base_url else None

    # Use the provider's underlying client to make a structured call
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=base_url,
        )

        response = await client.chat.completions.create(
            model=settings.openai_responses_model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2000,
        )

        raw_json = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_json)

    except Exception as e:
        logger.exception("audience_panel_synthesis_failed")
        raise ValueError(f"Panel synthesis failed: {e}") from e

    # Parse the response into a PopulationSpec
    injections_raw = parsed.get("injections", [])
    reasoning = parsed.get("reasoning", "No reasoning provided.")

    injections: List[PersonaInjection] = []
    for item in injections_raw:
        persona_data = item.get("persona", {})
        persona = PersonaSpec(
            name=persona_data.get("name", "Unnamed"),
            age=persona_data.get("age"),
            gender=persona_data.get("gender"),
            region=persona_data.get("region"),
            income=persona_data.get("income"),
            occupation=persona_data.get("occupation"),
            descriptors=persona_data.get("descriptors", []),
            weight=persona_data.get("weight", 1.0),
        )
        injections.append(
            PersonaInjection(
                persona=persona,
                weight_share=item.get("weight_share"),
            )
        )

    spec = PopulationSpec(injections=injections)
    return spec, reasoning


__all__ = ["parse_evidence", "synthesize_panel"]
