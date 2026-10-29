"""Shared access helpers; all workstreams use the application-owned supervisor."""

from fastapi import HTTPException
from ..supervisor import Conflict


def trip_for(app, user, trip_id):
    row = app.state.store.db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
    if not row or (user["role"] == "passenger" and row["owner_id"] != user["id"]):
        raise HTTPException(404, "Trip not found")
    return dict(row)


def visible_snapshot(app, user):
    result = app.state.core.snapshot()
    if result["trip"]:
        trip = result["trip"]
        if not user or (user["role"] == "passenger" and trip.get("owner_id") != user["id"]):
            result["trip"] = None
        else:
            trip.pop("owner_id", None)
    return result


def execute(fn, *args):
    try:
        return fn(*args)
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
