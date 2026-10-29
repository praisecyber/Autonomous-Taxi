import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from .storage import Store
from .supervisor import Supervisor, Conflict
from .navigation import POINTS
from .auth import Auth, digest
import time
from .accounts import router as account_router

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
        legacy_setting = os.getenv("TAXI_ALLOW_LEGACY_TOKEN", "auto")
        if legacy_setting not in {"auto", "0", "1"}:
            store.close()
            raise RuntimeError("TAXI_ALLOW_LEGACY_TOKEN must be auto, 0 or 1")
        legacy_enabled = legacy_setting == "1" or (
            legacy_setting == "auto" and not store.db.execute("SELECT 1 FROM users").fetchone()
        )
        app.state.auth = Auth(
            store,
            token,
            legacy_enabled=legacy_enabled,
            secure_cookie=os.getenv("TAXI_SECURE_COOKIES", "0") == "1",
        )

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

    app.include_router(account_router)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Validation responses must never echo submitted passwords or tokens.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
        )

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/") or request.url.path == "/admin":
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    async def authorize(request: Request):
        return app.state.auth.require(request, "operator")

    def trip_for(user, trip_id):
        row = app.state.store.db.execute("SELECT * FROM trips WHERE id=?", (trip_id,)).fetchone()
        if not row or (user["role"] == "passenger" and row["owner_id"] != user["id"]):
            raise HTTPException(404, "Trip not found")
        return dict(row)

    def visible_snapshot(user):
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

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/admin", include_in_schema=False)
    async def admin():
        return FileResponse(STATIC / "admin.html")

    @app.get("/account", include_in_schema=False)
    async def account():
        return FileResponse(STATIC / "account.html")

    @app.get("/api/health")
    async def health():
        return {
            "ok": app.state.core.reason != "supervisor_exception",
            "mode": "simulation",
            "hardware_motion_implemented": False,
        }

    @app.get("/api/stops")
    async def stops():
        return {
            "stops": app.state.core.config["stops"],
            "points": POINTS,
            "edges": app.state.core.config["edges"],
        }

    @app.get("/api/status")
    async def status(request: Request):
        return visible_snapshot(app.state.auth.identity(request, required=False))

    @app.post("/api/trips", status_code=201)
    async def start(body: TripRequest, request: Request):
        user = app.state.auth.require(request, "passenger", "operator")
        return execute(
            app.state.core.start,
            body.destination,
            user["id"] if user["role"] == "passenger" else None,
        )

    @app.get("/api/trips")
    async def trips(request: Request):
        user = app.state.auth.identity(request)
        if user["role"] == "passenger":
            return [
                dict(r)
                for r in app.state.store.db.execute(
                    "SELECT * FROM trips WHERE owner_id=? ORDER BY created_at DESC,id DESC LIMIT 100",
                    (user["id"],),
                )
            ]
        return app.state.store.trips()

    @app.get("/api/trips/{trip_id}")
    async def trip(trip_id: str, request: Request):
        return trip_for(app.state.auth.identity(request), trip_id)

    @app.post("/api/trips/{trip_id}/cancel")
    async def cancel(trip_id: str, request: Request):
        user = app.state.auth.require(request, "passenger", "operator")
        trip_for(user, trip_id)
        core = app.state.core
        if not core.trip or core.trip["id"] != trip_id or core.trip["status"] != "ACTIVE":
            raise HTTPException(409, "Trip is not the active mission")
        core.stop("trip_cancelled")
        return visible_snapshot(user)

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

    @app.get("/api/events")
    async def events(request: Request):
        app.state.auth.require(request, "operator", "admin")
        return app.state.store.events()

    @app.websocket("/ws/telemetry")
    async def telemetry(ws: WebSocket):
        # Read-only simulation telemetry; no commands accepted over this socket.
        origin = ws.headers.get("origin")
        expected_origin = (
            str(ws.base_url).replace("ws://", "http://").replace("wss://", "https://").rstrip("/")
        )
        if origin and origin != expected_origin:
            await ws.close(code=1008)
            return
        await ws.accept()
        try:
            while True:
                # Revalidate on every message so logout/disable/expiry takes effect.
                token = ws.cookies.get("taxi_session", "")
                row = (
                    app.state.store.db.execute(
                        """SELECT u.id,u.role FROM sessions s JOIN users u ON u.id=s.user_id
                       WHERE s.token_hash=? AND s.expires_at>? AND u.enabled=1""",
                        (digest(token), time.time()),
                    ).fetchone()
                    if token
                    else None
                )
                await ws.send_json(visible_snapshot(dict(row) if row else None))
                await asyncio.sleep(0.2)
        except (WebSocketDisconnect, RuntimeError):
            pass

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
