# Campus Taxi — Python + ESP32-CAM + Arduino

A runnable starting repository for the autonomous campus taxi project. The laptop application runs an A-to-B simulation, FastAPI backend, operator dashboard, telemetry and SQLite history. No ROS is required.

**v0.1 is a simulation and bench-communications foundation. Physical navigation, sensor drivers and motor actuation are not implemented.** The board starters never enable motors and the laptop rejects `TAXI_MODE=hardware`. Nothing in this release is approved for carrying passengers or road use.

## Run on Windows

Install Python 3.10+ and Git, extract this folder, then open PowerShell inside it:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m taxi
```

Open **http://127.0.0.1:8000**. The operator token is `local-dev-only` unless changed in `.env`. Python 3.11 or 3.12 also works: select the installed version when creating the environment. Activation is unnecessary. API reference: http://127.0.0.1:8000/docs.

Linux / macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/python -m taxi
```

Run one server process, one worker, and one vehicle supervisor. Do not add multiple Uvicorn workers: each would create a separate simulated vehicle. The default command listens only on loopback. Internet access is not needed after installing dependencies.

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
| Backend | Validated API, operator token, read-only telemetry WebSocket, SQLite | User roles, deployment authentication, dispatch |
| Brain | Route graph, deterministic simulated motion, stale-input gates and latched faults | Real perception, localization, closed-loop control |
| ESP32-CAM | AI Thinker camera capture + read-only UART telemetry + stop-request firmware starter | Confirm board, pins, credentials; bench test |
| Arduino | Uno bench parser; rejects motion, reports sensors unavailable | Confirm board/driver; implement real sensors and motor safety |
| AI models | Optional vision dependency group; no weights bundled | Benchmark/select a commercially suitable checkpoint |

## Project layout

```text
taxi/
  api.py                 REST, WebSocket, application lifecycle
  supervisor.py          Mission state machine and simulator
  navigation.py          Stops and shortest permitted routes
  storage.py             SQLite trips and events
  static/                Browser dashboard (no Node build needed)
firmware/
  esp32_cam/             AI Thinker camera / UART bench starter
  arduino/               Uno serial bench starter; no actuator pins
scripts/
  setup.ps1              Optional Windows installer
  camera_probe.py        Authenticated JPEG capture test
tests/                   Supervisor and API tests
docs/                    Architecture, protocol, hardware and Codex roadmap
```

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
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
