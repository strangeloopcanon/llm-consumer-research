"""FastAPI app exposing the simulation service."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .config import AppSettings, get_settings
from .models import SimulationRequest, SimulationResponse
from .orchestrator import run_simulation

app = FastAPI(title="SSR Synthetic Consumer Research", version="0.1.0")


@app.get("/health")
async def health(settings: AppSettings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "model": settings.openai_responses_model}


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(request: SimulationRequest) -> SimulationResponse:
    try:
        return await run_simulation(request)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


__all__ = ["app"]
