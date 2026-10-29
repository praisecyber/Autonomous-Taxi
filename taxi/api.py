import asyncio
import contextlib
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from .storage import Store
from .supervisor import Supervisor, Conflict
from .navigation import STOPS, POINTS, EDGES

STATIC = Path(__file__).parent / "static"


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: str


class Hazards(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obstacle: bool
    sensor_failed: bool
    link_failed: bool


def create_app(db_path=None, operator_token=None, run_loop=True):
    load_dotenv()
    if os.getenv("TAXI_MODE", "simulation") != "simulation":
        raise RuntimeError("Hardware motion is not implemented. TAXI_MODE must be simulation.")
    token = operator_token or os.getenv("TAXI_OPERATOR_TOKEN", "local-dev-only")
    if len(token) < 12:
        raise RuntimeError("Operator token must contain at least 12 characters")

    @asynccontextmanager
    async def lifespan(app):
        path = db_path or str(Path(os.getenv("TAXI_DATA_DIR", "runtime")) / "taxi.sqlite3")
        store = Store(path)
        core = Supervisor(store)
        app.state.core, app.state.store = core, store

        async def drive():
            while True:
                await asyncio.sleep(0.05)
                try:
                    core.step()
                except Exception:
                    # Fail closed in memory even when persistence itself failed.
                    core.speed, core.state, core.reason = 0.0, "FAULT", "supervisor_exception"
                    raise

        task = asyncio.create_task(drive()) if run_loop else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            try:
                core.stop("server_shutdown", "INTERRUPTED")
            finally:
                store.close()

    app = FastAPI(title="Campus Taxi Prototype", version="0.1.0", lifespan=lifespan)

    async def authorize(authorization: str = Header(default="")):
        if not secrets.compare_digest(authorization, "Bearer " + token):
            raise HTTPException(401, "Valid operator token required")

    def execute(fn, *args):
        try:
            return fn(*args)
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    async def health():
        return {
            "ok": app.state.core.reason != "supervisor_exception",
            "mode": "simulation",
            "hardware_motion_implemented": False,
        }

    @app.get("/api/stops")
    async def stops():
        return {"stops": STOPS, "points": POINTS, "edges": EDGES}

    @app.get("/api/status")
    async def status():
        return app.state.core.snapshot()

    @app.post("/api/trips", dependencies=[Depends(authorize)], status_code=201)
    async def start(body: TripRequest):
        return execute(app.state.core.start, body.destination)

    @app.get("/api/trips", dependencies=[Depends(authorize)])
    async def trips():
        return app.state.store.trips()

    @app.get("/api/trips/{trip_id}", dependencies=[Depends(authorize)])
    async def trip(trip_id: str):
        rows = app.state.store.db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
        if not rows:
            raise HTTPException(404, "Trip not found")
        return dict(rows)

    @app.post("/api/trips/{trip_id}/cancel", dependencies=[Depends(authorize)])
    async def cancel(trip_id: str):
        core = app.state.core
        if not core.trip or core.trip["id"] != trip_id or core.trip["status"] != "ACTIVE":
            raise HTTPException(409, "Trip is not the active mission")
        core.stop("trip_cancelled")
        return core.snapshot()

    @app.post("/api/operator/stop", dependencies=[Depends(authorize)])
    async def stop():
        app.state.core.stop()
        return app.state.core.snapshot()

    @app.post("/api/operator/rearm", dependencies=[Depends(authorize)])
    async def rearm():
        execute(app.state.core.rearm)
        return app.state.core.snapshot()

    @app.post("/api/simulation/reset", dependencies=[Depends(authorize)])
    async def reset():
        execute(app.state.core.reset)
        return app.state.core.snapshot()

    @app.post("/api/simulation/hazards", dependencies=[Depends(authorize)])
    async def hazards(body: Hazards):
        core = app.state.core
        core.obstacle, core.sensor_failed, core.link_failed = (
            body.obstacle,
            body.sensor_failed,
            body.link_failed,
        )
        core.store.event("hazards", body.model_dump())
        # Apply an obstacle stop before responding, rather than waiting for the next timer.
        core.step()
        return core.snapshot()

    @app.get("/api/events", dependencies=[Depends(authorize)])
    async def events():
        return app.state.store.events()

    @app.websocket("/ws/telemetry")
    async def telemetry(ws: WebSocket):
        # Read-only simulation telemetry; no commands accepted over this socket.
        await ws.accept()
        try:
            while True:
                await ws.send_json(app.state.core.snapshot())
                await asyncio.sleep(0.2)
        except (WebSocketDisconnect, RuntimeError):
            pass

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
