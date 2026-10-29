# Separate frontend and backend

Run both processes from the repository root. Python 3.10+ and Node.js 22+ are required.
The source and responsibilities are separate:

| Folder | Responsibility |
|---|---|
| `frontend/public/` | Browser pages, styles and JavaScript; no database access |
| `frontend/server.mjs` | Serves pages and forwards HTTP/WebSocket requests to the API |
| `backend/taxi/` | API, sessions, roles, trip ownership, simulator and storage |
| `backend/tests/` | Backend unit/API regression tests |
| `frontend/tests/` | Frontend server and API proxy tests |

## Start locally

Install Python dependencies once (or again after the folder move):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Terminal 1 — backend:

```bash
.venv/bin/python -m taxi
```

Terminal 2 — frontend:

```bash
node frontend/server.mjs
```

On Windows use `.\.venv\Scripts\python.exe` for Python commands. There is no frontend
package installation or build step. Open the frontend on port 3000; use `/operator`,
`/account` and `/admin` there. API documentation is available at `/docs` through the proxy,
or directly from the backend on port 8000. The backend deliberately returns 404 for UI
pages and `/static` assets.

The project root's `.env` and `runtime/` paths are unchanged. Do not move or delete an
existing database. `python -m taxi.manage` still provides account bootstrap and offline
backup/restore from the root. After bootstrap, restart the backend; the frontend can stay
running. See [accounts and API contract](ADMIN-ACCOUNTS.md).

## How they communicate

The browser calls same-origin `/api/...` endpoints with Fetch and `/ws/telemetry` with
WebSocket. The frontend server forwards these to a fixed local backend. Cookies and
CSRF headers are forwarded, so login, logout, password changes and role restrictions use
the same backend rules. No shared database, Python imports or supervisor exist in the
frontend. The backend owns one supervisor regardless of connected pages.

Examples:

- `GET /api/stops`: configured destinations.
- `POST /api/auth/login`: creates an account session.
- `POST /api/trips` with `{"destination":"B"}`: starts an authorized simulated trip.
- `/ws/telemetry`: read-only simulation updates.

Keep UI requests relative to the browser origin. Do not point browser Fetch directly at
a different port or add wildcard CORS to make login work. The proxy retains the browser
Host/Origin and strips untrusted forwarding headers so existing origin/CSRF checks work.
The local frontend accepts loopback Host values and local HTTP API targets only. Its
static-file handler cannot serve backend files, `.env` or files outside `frontend/public`.

## Optional port overrides

Defaults are frontend 3000 and backend 8000. To use another backend/frontend port:

```bash
.venv/bin/python -m uvicorn taxi.api:create_app --factory --host 127.0.0.1 --port 8100
TAXI_API_URL=http://127.0.0.1:8100 TAXI_FRONTEND_PORT=3100 node frontend/server.mjs
```

PowerShell equivalent for the frontend:

```powershell
$env:TAXI_API_URL = 'http://127.0.0.1:8100'
$env:TAXI_FRONTEND_PORT = '3100'
node frontend/server.mjs
```

Node reads these from the process environment; Python's dotenv loader does not configure
Node. Backend `.env` values continue to be read by the Python application. Open the chosen
frontend port. Never run multiple backend workers or start two backends on one database.

## Validation

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
node --check frontend/server.mjs
node --check frontend/public/app.js
node --check frontend/public/admin.js
node --check frontend/public/account.js
node --check frontend/public/operator.js
node --test frontend/tests/server.test.mjs
```

Optional real-browser integration:

```bash
.venv/bin/python -m pip install -e '.[dev,browser]'
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium
```

The browser script starts and cleans up separate frontend/backend processes and a
throwaway database. It verifies account permissions, passenger ownership, operator
controls and WebSocket telemetry through the actual proxy, not a mocked API.

For production, serve the frontend behind an HTTPS reverse proxy routing `/api` and `/ws`
to the backend, with WebSocket upgrades and trusted Host/Origin handling. The bundled Node
server is local development tooling. Hardware motion remains unavailable.
