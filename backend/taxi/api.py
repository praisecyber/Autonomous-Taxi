import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .deployment import Deployment
from .locking import DatabaseLease
from dotenv import load_dotenv
from .storage import Store
from .supervisor import Supervisor
from .navigation import POINTS
from .auth import Auth, digest
import time
from .routers.admin import router as account_router
from .routers.operator import router as operator_router
from .routers.passenger import router as passenger_router
from .routers.common import visible_snapshot
from .swagger import install_swagger


def create_app(db_path=None, operator_token=None, run_loop=True):
    load_dotenv()
    deployment = Deployment.from_environment()
    if os.getenv("TAXI_MODE", "simulation") != "simulation":
        raise RuntimeError("Hardware motion is not implemented. TAXI_MODE must be simulation.")
    token = operator_token or os.getenv("TAXI_OPERATOR_TOKEN", "local-dev-only")
    if len(token) < 12:
        raise RuntimeError("Operator token must contain at least 12 characters")

    @asynccontextmanager
    async def lifespan(app):
        path = db_path or str(Path(os.getenv("TAXI_DATA_DIR", "runtime")) / "taxi.sqlite3")
        with DatabaseLease(path):
            store = Store(path)
            if (
                deployment.production
                and not store.db.execute(
                    "SELECT 1 FROM users WHERE role='admin' AND enabled=1"
                ).fetchone()
            ):
                store.close()
                raise RuntimeError("Bootstrap an enabled admin before starting production")
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

    app = FastAPI(title="Campus Taxi Prototype", version="0.1.0", lifespan=lifespan, docs_url=None)

    if deployment.hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(deployment.hosts))
    app.include_router(account_router)
    app.include_router(operator_router)
    app.include_router(passenger_router)

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
        if (
            deployment.production
            and request.url.scheme != "https"
            and request.url.path != "/api/health"
        ):
            return JSONResponse(status_code=403, content={"detail": "HTTPS is required"})
        response = await call_next(request)
        if request.url.path.startswith("/api/") or request.url.path == "/admin":
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

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
        return visible_snapshot(app, app.state.auth.identity(request, required=False))

    @app.get("/api/events")
    async def events(request: Request):
        app.state.auth.require(request, "operator", "admin")
        return app.state.store.events()

    @app.websocket("/ws/telemetry")
    async def telemetry(ws: WebSocket):
        # Read-only simulation telemetry; no commands accepted over this socket.
        if deployment.production and ws.url.scheme != "wss":
            await ws.close(code=1008)
            return
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
                       WHERE s.token_hash=? AND s.expires_at>? AND u.enabled=1 AND u.must_change_password=0""",
                        (digest(token), time.time()),
                    ).fetchone()
                    if token
                    else None
                )
                await ws.send_json(visible_snapshot(app, dict(row) if row else None))
                await asyncio.sleep(0.2)
        except (WebSocketDisconnect, RuntimeError):
            pass

    install_swagger(app)
    return app
