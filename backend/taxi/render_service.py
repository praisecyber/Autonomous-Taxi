"""Render entry point: one API supervisor and same-origin packaged frontend."""

import os
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import create_app


def create_render_app():
    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
    if not hostname:
        raise RuntimeError("Render must supply RENDER_EXTERNAL_HOSTNAME")
    # Use the platform-assigned host, never a wildcard allowed host.
    os.environ["TAXI_ALLOWED_HOSTS"] = hostname
    app = create_app()
    public = Path(__file__).resolve().parents[2] / "frontend" / "public"
    # Source deployment layout is backend/taxi; installed module layout needs an
    # explicit public directory, set by the Render start script.
    public = Path(os.environ.get("TAXI_FRONTEND_ROOT", str(public)))
    app.mount("/static", StaticFiles(directory=public), name="frontend-static")
    pages = {
        "/": "index.html", "/operator": "index.html", "/passenger": "passenger.html",
        "/admin": "admin.html", "/account": "account.html", "/diagnostics": "diagnostics.html",
    }
    def page_handler(filename):
        def endpoint():
            return FileResponse(public / filename, headers={"Cache-Control": "no-store"})
        return endpoint

    for route, filename in pages.items():
        app.add_api_route(route, page_handler(filename), methods=["GET"], include_in_schema=False)
    return app
