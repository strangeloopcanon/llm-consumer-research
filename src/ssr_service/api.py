"""FastAPI app exposing the simulation service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .audience_builder import parse_evidence, synthesize_panel
from .config import AppSettings, get_settings
from .db import delete_run, get_run, init_db, list_runs, save_run
from .models import (
    PanelPreviewResponse,
    PersonaGroupSummary,
    SimulationRequest,
    SimulationResponse,
)
from .orchestrator import preview_panel, run_simulation
from .personas import get_persona_library


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="SSR Synthetic Consumer Research",
    version="0.2.0",
    lifespan=lifespan,
)

app_settings = get_settings()

app.add_middleware(
    CORSMiddleware,  # ty: ignore[invalid-argument-type]
    allow_origins=app_settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(settings: AppSettings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "model": settings.openai_responses_model}


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(request: SimulationRequest) -> SimulationResponse:
    try:
        response = await run_simulation(request)

        # Persist the run to the database
        label_parts = []
        if request.concept and request.concept.title:
            label_parts.append(request.concept.title)
        if request.persona_group:
            label_parts.append(request.persona_group)
        label_parts.append(f"n={response.aggregate.sample_n}")
        label = " · ".join(label_parts) if label_parts else None

        run_id = save_run(
            request_data=request.model_dump(mode="json"),
            response_data=response.model_dump(mode="json"),
            label=label,
        )
        # Inject the run_id into metadata for client convenience
        response.metadata["run_id"] = run_id

        return response
    except (ValueError, RuntimeError) as exc:
        logging.error("Simulation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("An unexpected error occurred during simulation.")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.post("/panel-preview", response_model=PanelPreviewResponse)
async def panel_preview(request: SimulationRequest) -> PanelPreviewResponse:
    try:
        return await preview_panel(request)
    except (ValueError, RuntimeError) as exc:
        logging.error("Panel preview error: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("An unexpected error occurred during panel preview.")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.get("/persona-groups", response_model=list[PersonaGroupSummary])
async def persona_groups(
    settings: AppSettings = Depends(get_settings),
) -> list[PersonaGroupSummary]:
    library = get_persona_library(settings.persona_library_path)
    groups = list(library.groups().values())
    groups.sort(key=lambda group: group.name)
    return [
        PersonaGroupSummary(
            name=group.name,
            description=group.description,
            persona_count=len(group.personas),
            source=group.source,
        )
        for group in groups
    ]


# ============================================================================
# Run History Endpoints
# ============================================================================


@app.get("/runs")
async def get_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> List[Dict[str, Any]]:
    """List simulation runs, most recent first."""
    return list_runs(limit=limit, offset=offset)


@app.get("/runs/{run_id}")
async def get_run_by_id(run_id: str) -> Dict[str, Any]:
    """Get a specific run by ID, including full request and response."""
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.delete("/runs/{run_id}")
async def delete_run_by_id(run_id: str) -> Dict[str, str]:
    """Delete a specific run by ID."""
    deleted = delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "deleted", "id": run_id}


# ============================================================================
# Audience Builder Endpoints
# ============================================================================




@app.post("/audience/build")
async def build_audience(
    files: List[UploadFile] = File(...),
    target_description: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    """Build a PopulationSpec from uploaded evidence files.

    Accepts CSV, PDF, JSON, or text files. Returns a PopulationSpec
    that can be used directly in a /simulate request.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    # Parse all uploaded files
    file_contents: List[tuple[str, bytes | str]] = []
    for upload in files:
        content = await upload.read()
        file_contents.append((upload.filename or "unknown", content))

    try:
        evidence_summary = parse_evidence(file_contents)
        spec, reasoning = await synthesize_panel(
            evidence_summary=evidence_summary,
            target_description=target_description,
        )
        return {
            "population_spec": spec.model_dump(mode="json"),
            "reasoning": reasoning,
            "evidence_summary_length": len(evidence_summary),
        }
    except ValueError as exc:
        logging.error("Audience build error: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("Unexpected error during audience build.")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


__all__ = ["app"]
