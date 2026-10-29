"""Local Swagger UI and the authentication contract for the HTTP API."""

from pathlib import Path

from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

ASSETS = Path(__file__).with_name("docs_assets")
DESCRIPTION = """Campus Taxi simulation API. No physical vehicle motion is implemented.

**Account login:** execute `POST /api/auth/login`, then try authorized endpoints. The
browser keeps the HttpOnly session cookie; this Swagger page adds the CSRF header for
session mutations automatically. You can also sign in through `/account` or `/admin`.

**Permissions:** passengers request/read/cancel their own trips; operators control the
simulator and read records; administrators manage accounts, reports and configuration.
Administrators do not inherit operator command authority. Configuration saves require
READY at A with no trip and the current configuration version.

**Local demo token:** use Authorize → LocalOperatorToken only when legacy-token access
is enabled. Enter the token without the `Bearer` prefix. It never grants admin access.
Authorizations are not persisted across page reloads. AccountSession cookies are issued
by login, not entered manually in Authorize.

**Telemetry:** `/ws/telemetry` is a read-only WebSocket (not executable in Swagger).
Use the browser's current host with `ws://` or `wss://`; session/ownership rules apply.
"""


def install_swagger(app):
    app.mount("/docs/assets", StaticFiles(directory=ASSETS), name="swagger-assets")

    @app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    async def swagger():
        return HTMLResponse(
            """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Taxi API · Swagger</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="/docs/assets/swagger-ui.css"></head>
<body><div id="swagger-ui"></div>
<script src="/docs/assets/swagger-ui-bundle.js"></script>
<script src="/docs/assets/swagger-init.js"></script></body></html>""",
            headers={"Cache-Control": "no-store"},
        )

    def openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=DESCRIPTION,
            routes=app.routes,
            tags=[
                {"name": "Status", "description": "Public simulated status and configured stops."},
                {
                    "name": "Accounts",
                    "description": "Login, current identity, logout and passwords.",
                },
                {"name": "Trips", "description": "Passenger-owned trips and operator trip access."},
                {"name": "Operator", "description": "Operator-only simulation controls."},
                {
                    "name": "Administration",
                    "description": "Administrator-only records and settings.",
                },
            ],
        )
        schema["components"].setdefault("securitySchemes", {}).update(
            {
                "AccountSession": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "taxi_session",
                    "description": "HttpOnly cookie set by POST /api/auth/login. Use login rather than manually authorizing this cookie.",
                },
                "LocalOperatorToken": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Optional local-demo operator token. Disabled once accounts exist by default; no admin authority.",
                },
            }
        )
        public = {"/api/health", "/api/stops", "/api/status", "/api/auth/login"}
        for path, operations in schema["paths"].items():
            for method, operation in operations.items():
                if method not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if path.startswith("/api/admin/"):
                    tag = "Administration"
                elif path.startswith("/api/auth/"):
                    tag = "Accounts"
                elif path.startswith(("/api/operator/", "/api/simulation/")):
                    tag = "Operator"
                elif path.startswith(("/api/trips", "/api/passenger/")):
                    tag = "Trips"
                else:
                    tag = "Status"
                operation["tags"] = [tag]
                if path not in public:
                    operation["security"] = [{"AccountSession": []}]
                    if tag != "Administration" and path != "/api/auth/password":
                        operation["security"].append({"LocalOperatorToken": []})
                    operation["responses"].setdefault(
                        "401",
                        {
                            "description": "Sign-in required, invalid credentials or expired session."
                        },
                    )
                    operation["responses"].setdefault(
                        "403", {"description": "Role, CSRF token or Origin not permitted."}
                    )
                if method in {"post", "put", "patch", "delete"} and path != "/api/auth/login":
                    operation["parameters"] = [
                        *operation.get("parameters", []),
                        {
                            "name": "X-Taxi-CSRF",
                            "in": "header",
                            "required": False,
                            "description": "Required with account sessions; automatically supplied by this Swagger page. Not needed for the local bearer-token demo.",
                            "schema": {"type": "string"},
                        },
                    ]
                    operation["responses"].setdefault(
                        "409",
                        {
                            "description": "Mission state, configuration version or account conflict."
                        },
                    )
        for model in schema["components"].get("schemas", {}).values():
            for name, field in model.get("properties", {}).items():
                if name in {"password", "current_password", "new_password"}:
                    field.update({"format": "password", "writeOnly": True})
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
