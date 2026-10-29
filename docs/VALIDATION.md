# Validation record — 23 October 2026

## Passed in the development environment

- Editable Python package installation with development dependencies.
- 14 pytest cases: A-to-B arrival and return routing, obstacle fault latch, explicit rearm, sensor/link timeouts, supervisor stall, cancellation, duplicate mission rejection, invalid destinations, interrupted-trip restart handling, API authorization, validation, and WebSocket snapshot delivery.
- Live server check using real HTTP and WebSocket connections: A-to-B mission completed, stopped at B, and saved its terminal status in SQLite.
- Ruff lint check and Python bytecode compilation.
- Node JavaScript syntax check of the dashboard code.

Tests ran on Python 3.12. GitHub Actions is configured for Python 3.10 and 3.12; those remote CI jobs have not run yet. The installed Starlette test client emitted an httpx deprecation warning; tests passed.

## Not established

- Browser interaction / visual review: attempted headless Chromium setup, but the browser download was unavailable. API/static-file checks and JavaScript syntax checks do not establish browser QA.
- Firmware compilation: PlatformIO commands were attempted, but platform/toolchain downloads did not finish in this environment. Neither firmware target is claimed to compile successfully yet.
- Actual camera, UART, sensors, driver, physical stopping or autonomous movement: no hardware connected.
- Perception accuracy, localization accuracy, physical timing or stopping distance: not measured.

## Reproduce locally

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
node --check frontend/public/app.js
```

For board builds, follow HARDWARE.md and record compiler logs and exact board settings. For browser QA, run the demo steps in README.md at desktop and phone widths.
