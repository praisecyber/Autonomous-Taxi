# Architecture and ownership

## Running laptop application

The source is split into `frontend/` and `backend/`. A Node.js frontend server on loopback
port 3000 serves `frontend/public` and forwards `/api/*` HTTP requests and `/ws/telemetry`
upgrades to the FastAPI backend on port 8000. FastAPI serves no HTML or static files.
The backend package is `backend/taxi`; Python installation/test commands still run from
the repository root using pyproject.toml. See [startup and API boundary](FRONTEND-BACKEND.md).

The FastAPI lifespan creates one Store and one Supervisor. A 20 Hz asynchronous task advances simulation; a read-only WebSocket publishes snapshots at 5 Hz. Request handlers do not await while mutating the core, so mutations are serialized on the event loop. SQLite writes are synchronous and suitable only for this small prototype; a storage error faults motion in memory. A blocked event loop faults an active simulation when its next tick exceeds the configured timing window.

```mermaid
flowchart TD
  UI[Browser dashboard] --> Frontend[Frontend server :3000]
  Frontend -->|HTTP API / WebSocket proxy| API[FastAPI :8000]
  API --> Core[Single supervisor]
  Core --> Nav[Route graph and simulated movement]
  Nav --> Core
  Core --> DB[(SQLite trips and events)]
  Core -->|Read-only snapshots| WS[Telemetry WebSocket]
  WS --> UI
```

The graph coordinates are virtual metres; A, B and C are stops and J is a junction. A shortest graph route is selected before simulation begins. This version follows ideal geometry; it has no vehicle dynamics, acceleration model, learned perception, lane detection or physical localization.

## States

- READY: no movement; permits a mission only at a named stop with healthy inputs.
- ACTIVE: one trip owns the simulated vehicle.
- COMPLETE: destination reached; zero speed and terminal COMPLETED trip.
- STOPPED: operator stop/cancel; zero speed and CANCELLED trip.
- FAULT: latched obstacle, stale sensor, lost link, timing or supervisor exception.

Clearing a fault input never resumes movement. Explicit rearm returns READY. If stopped between stops, a simulation reset is required before a new trip. Reset is rejected while ACTIVE. No equivalent physical teleport/reset is implied.

## Hardware direction (not integrated with driving)

```mermaid
flowchart TD
  Host[Python laptop] -->|GET capture / telemetry| ESP[ESP32-CAM bench firmware]
  ESP -->|JPEG / UART text| Host
  ESP -->|STOP request only| MCU[Arduino bench firmware]
  MCU -->|Disarmed telemetry| ESP
  MCU -.-> Future[Future driver and actuator integration]
```

ESP32 exposes authenticated `/capture`, `/telemetry`, and `/stop` on local HTTP. There is no command stream, continuous MJPEG or motion endpoint yet. Python camera_probe tests one image. The application simulator is intentionally independent of the board starters.

Camera work must eventually run outside the supervisor loop with bounded latest-frame queues. A real adapter must preserve freshness through every hop, reject replay, separate acknowledgements from measured stopping, and leave Arduino safety independent of the host.

## Access and deployment

Account sessions enforce passenger/operator/admin permissions and trip ownership. The
legacy bearer-token operator demo is available only before accounts exist by default.
See [account and integration contract](ADMIN-ACCOUNTS.md). Public simulated position,
stop definitions, API docs and redacted telemetry remain local development features.

The browser uses its frontend origin for all requests. The local frontend proxy preserves
Host/Origin and HttpOnly cookies, strips supplied forwarding headers, restricts accepted
hosts to loopback and uses a fixed local API target. Backend CSRF/origin and WebSocket
origin checks stay enabled; no wildcard credentialed CORS is needed. The Node server is
for local development. HTTPS deployment needs a trusted production reverse proxy serving
the frontend and routing /api and /ws to the single backend worker.

## Sources

- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- Espressif camera API: https://github.com/espressif/esp32-camera
- PlatformIO AI Thinker target: https://docs.platformio.org/en/latest/boards/espressif32/esp32cam.html
