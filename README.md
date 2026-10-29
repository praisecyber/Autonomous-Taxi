# Campus Taxi — Python + ESP32-CAM + Arduino

A runnable starting repository for the autonomous campus taxi project. The laptop application runs an A-to-B simulation, FastAPI backend, operator dashboard, telemetry and SQLite history. No ROS is required.

**v0.1 is a simulation and bench-communications foundation. Physical navigation, sensor drivers and motor actuation are not implemented.** The board starters never enable motors and the laptop rejects `TAXI_MODE=hardware`. Nothing in this release is approved for carrying passengers or road use.

## Run on Windows

Install Python 3.10+, Node.js 22+ and Git, extract this folder, then open PowerShell inside it:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m taxi
```

In a **second terminal**, from the same repository root, start the frontend:

```bash
node frontend/server.mjs
```

Open **http://127.0.0.1:3000**. The operator token is `local-dev-only` unless changed in `.env`. Python 3.11 or 3.12 also works: select the installed version when creating the environment. Activation is unnecessary. Swagger API explorer: **http://127.0.0.1:3000/docs** (also available directly on backend port 8000). The OpenAPI schema is `/openapi.json`. Swagger assets are served locally; no CDN is needed. See [Swagger usage](docs/SWAGGER.md).

Linux / macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
test -f .env || cp .env.example .env
.venv/bin/python -m taxi
```

Start `node frontend/server.mjs` in a second terminal on Linux/macOS too. The frontend
needs no npm install or build. Run these commands from the repository root so `.env` and
`runtime/` keep their existing locations. See [separate frontend/backend development](docs/FRONTEND-BACKEND.md).

Run one backend process, one worker, and one vehicle supervisor. Do not add multiple Uvicorn workers: each would create a separate simulated vehicle. The default command listens only on loopback. Internet access is not needed after installing dependencies.

The **Records** link opens `/admin` for administrator accounts: paginated trip/event
records, stored-data summaries, user access management and versioned simulation
configuration. `/account` provides shared sign-in, password changes and an owned-trip
integration screen for passengers. Operator accounts use the original dashboard.

To create the first administrator, **stop the server** and run:

```bash
.venv/bin/python -m taxi.manage create-admin --username your-admin-name
```

Enter a new password at the hidden prompt, then restart `.venv/bin/python -m taxi`.
No default admin account or password is supplied. The bootstrap command runs only while
there is no enabled admin. Further accounts are created in `/admin`.

`TAXI_ALLOW_LEGACY_TOKEN=auto` (the default) keeps the original operator-token demo working
only while no accounts exist. Once accounts exist, sign in at `/account`; operator
sessions are used by the dashboard automatically. `0` disables the legacy token entirely;
`1` is an explicit local-demo override and must not be used for a shared account service.
Before HTTPS deployment, set `TAXI_SECURE_COOKIES=1`; the default supports HTTP loopback
only. This remains a single-process simulation, not a production deployment.

See [accounts, roles, migrations and backup/restore](docs/ADMIN-ACCOUNTS.md) and the
[Member 3 validation record](docs/ADMIN-RECORDS.md).

## Interfaces, design and backend brain

The frontend now includes **Passenger** (`/passenger`), **Operator** (`/operator`),
**Admin** (`/admin`) and **Diagnostics** (`/diagnostics`), plus shared account access
at `/account`. All use the green/yellow/black palette and `frontend/public/shared.css`.
Choose a destination on Passenger, supervise missions on Operator, manage authorized
records/configuration on Admin, and inspect simulated validity/missing hardware on Diagnostics.

Stale or disconnected telemetry is explicitly labelled, and current measurements/progress
become unavailable. Stop is a prominent software-only action, including on phones.
The planner, supervisor, perception scripts and weights remain backend-owned; see
[backend brain boundaries](backend/README.md#backend-owned-brain).
See [frontend validation and accessibility review](docs/FRONTEND-REVIEW.md).

## Try the full demo

1. Start at **A — Engineering**, select **B — Library**, and start the simulated trip.
2. Watch the vehicle follow A → J → B. The 10 m virtual journey takes roughly 13 seconds.
3. Inject an obstacle. The mission becomes FAULTED and the vehicle stops.
4. Clear the obstacle. The fault stays latched until you press Rearm.
5. A vehicle stopped between named stops cannot start another mission. Reset to A for the next test; this teleports only the simulator.
6. Inject frozen sensors or a lost link. Updates expire after 0.5 seconds and fault the trip.
7. Try A → C, inspect history, then stop/restart the server. Active trips become INTERRUPTED; a server restart never resumes a mission.

All positions, distances and fault inputs in the dashboard are simulated. Speed / timing constants are demonstration values, not physical vehicle settings. The Stop button is a software simulation stop, not a physical emergency stop.

## What is included

| Component | Implemented now | Next integration |
|---|---|---|
| Dashboard | Route map, trips, status, fault injection, stop/rearm/reset, history | Passenger accounts and real vehicle telemetry |
| Backend | Validated API, accounts/roles, trip ownership, read-only telemetry WebSocket, SQLite | Deployment authentication, dispatch |
| Brain | Route graph, deterministic simulated motion, stale-input gates and latched faults | Real perception, localization, closed-loop control |
| ESP32-CAM | AI Thinker camera capture + read-only UART telemetry + stop-request firmware starter | Confirm board, pins, credentials; bench test |
| Arduino | Uno bench parser; rejects motion, reports sensors unavailable | Confirm board/driver; implement real sensors and motor safety |
| AI models | Optional vision dependency group; no weights bundled | Benchmark/select a commercially suitable checkpoint |

## Project layout

```text
frontend/
  public/                HTML, CSS and browser JavaScript
  server.mjs             Local frontend server; forwards /api and /ws
  tests/                 Frontend/proxy tests
backend/
  vendor/                Optional backend-only third-party references
  taxi/                  FastAPI, accounts, supervisor, navigation and SQLite
  tests/                 Backend API, ownership and simulator tests
  api.py                 Compatibility ASGI entry point
pyproject.toml           Python dependencies and backend package configuration
firmware/                ESP32-CAM and Arduino bench starters
scripts/                 Setup, camera probe and browser integration checks
docs/                    Architecture, protocol, hardware and team handoff
```

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
node --check frontend/public/app.js
node --check frontend/public/admin.js
node --check frontend/public/account.js
node --check frontend/public/operator.js
node --test frontend/tests/server.test.mjs
```

## Clone from GitHub

```bash
git clone https://github.com/praisecyber/Autonomous-Taxi.git
cd Autonomous-Taxi
```

Follow the Windows or Linux setup above, then continue work with Codex. Commit and push your changes from this folder. `.env`, firmware `secrets.h`, recordings, model weights, runtime data and virtual environments are excluded from Git. Do not commit credentials.

## Continue with Codex

Read `AGENTS.md` and `docs/ROADMAP.md`. First run the tests, then tackle one milestone at a time. Hardware motion stays unavailable until the exact board, driver, steering method, feedback sensors and emergency-stop wiring are confirmed. Do not replace missing sensors with invented healthy readings.

This repository does not declare a redistribution licence for your original application code; choose one before publishing it for third-party reuse. Dependencies and any future model weights retain their own licences. No pretrained AI weights are included.
