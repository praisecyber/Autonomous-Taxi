"""Owned passenger trips and operator trip integration on one shared supervisor."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from .common import execute, trip_for, visible_snapshot

router = APIRouter()


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: str


@router.post("/api/passenger/book", status_code=201)
@router.post("/api/trips", status_code=201)
async def start(body: TripRequest, request: Request):
    user = request.app.state.auth.require(request, "passenger", "operator")
    return execute(
        request.app.state.core.start,
        body.destination,
        user["id"] if user["role"] == "passenger" else None,
    )


@router.get("/api/trips")
async def trips(request: Request):
    user = request.app.state.auth.identity(request)
    if user["role"] == "passenger":
        return [
            dict(r)
            for r in request.app.state.store.db.execute(
                "SELECT * FROM trips WHERE owner_id=? ORDER BY created_at DESC,id DESC LIMIT 100",
                (user["id"],),
            )
        ]
    return request.app.state.store.trips()


@router.get("/api/trips/{trip_id}")
async def trip(trip_id: str, request: Request):
    return trip_for(request.app, request.app.state.auth.identity(request), trip_id)


@router.post("/api/trips/{trip_id}/cancel")
async def cancel(trip_id: str, request: Request):
    user = request.app.state.auth.require(request, "passenger", "operator")
    trip_for(request.app, user, trip_id)
    core = request.app.state.core
    if not core.trip or core.trip["id"] != trip_id or core.trip["status"] != "ACTIVE":
        raise HTTPException(409, "Trip is not the active mission")
    core.stop("trip_cancelled")
    return visible_snapshot(request.app, user)
