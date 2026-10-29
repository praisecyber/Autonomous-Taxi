"""Operator-only commands; no global supervisor or telemetry-driven movement."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from .common import execute
from .passenger import TripRequest

router = APIRouter()


class Hazards(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obstacle: bool
    sensor_failed: bool
    link_failed: bool


async def authorize(request: Request):
    return request.app.state.auth.require(request, "operator")


@router.post("/api/operator/start", dependencies=[Depends(authorize)], status_code=201)
async def start(body: TripRequest, request: Request):
    return execute(request.app.state.core.start, body.destination)


@router.post("/api/operator/stop", dependencies=[Depends(authorize)])
async def stop(request: Request):
    request.app.state.core.stop()
    return request.app.state.core.snapshot()


@router.post("/api/operator/rearm", dependencies=[Depends(authorize)])
async def rearm(request: Request):
    execute(request.app.state.core.rearm)
    return request.app.state.core.snapshot()


@router.post("/api/simulation/reset", dependencies=[Depends(authorize)])
async def reset(request: Request):
    execute(request.app.state.core.reset)
    return request.app.state.core.snapshot()


@router.post("/api/simulation/hazards", dependencies=[Depends(authorize)])
async def hazards(body: Hazards, request: Request):
    core = request.app.state.core
    core.obstacle, core.sensor_failed, core.link_failed = (
        body.obstacle,
        body.sensor_failed,
        body.link_failed,
    )
    core.store.event("hazards", body.model_dump())
    # Apply an obstacle stop before responding, rather than waiting for the next timer.
    core.step()
    return core.snapshot()
