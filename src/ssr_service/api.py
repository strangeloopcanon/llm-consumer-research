"""FastAPI app exposing the simulation service."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import AppSettings, get_settings
from .models import SimulationRequest, SimulationResponse
from .orchestrator import run_simulation

app = FastAPI(title="SSR Synthetic Consumer Research", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development convenience
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
        return await run_simulation(request)
    except (ValueError, RuntimeError) as exc:
        logging.error("Simulation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("An unexpected error occurred during simulation.")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


__all__ = ["app"]
