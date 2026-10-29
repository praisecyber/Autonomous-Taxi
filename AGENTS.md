# Codex project instructions

## Goal and current scope
Build a campus taxi using Python on a laptop, ESP32-CAM for camera / communication and Arduino for local sensor / motor control. No ROS dependency. Read README.md and docs/ROADMAP.md before substantial work.

v0.1 implements a simulation, backend, dashboard and bench-only firmware starters. Physical navigation and actuation are NOT implemented. Do not represent simulated data as real telemetry.

## Work rules
- Frontend pages/assets live in frontend/public; backend Python code is backend/taxi and backend tests are backend/tests.
- For the provisioned real local database, use `deploy/start-local-https.sh`; read deploy/README.md. Do not start a second backend against that database. For isolated development databases, run both processes from the repository root: `python -m taxi` and `node frontend/server.mjs`. The frontend proxies /api and /ws; do not add a second supervisor or permissive CORS to connect them.
- Run `python -m pytest -q` and `ruff check .` after Python changes.
- Run `node --check frontend/public/app.js` after browser JS changes.
- Keep dependencies in pyproject.toml. Keep package discovery limited to taxi.
- Keep secrets and generated runtime data out of Git.
- One server process owns one supervisor. Do not add multiple API workers.
- Preserve terminal trip statuses and latched faults. Reconnect never authorizes motion.
- Maintain separate application stop and physical emergency-stop concepts.
- Never enable physical outputs with guessed pins, driver types or safety thresholds.
- Before motor integration, record confirmed hardware in docs/HARDWARE.md and add fault-injection tests for the complete host → ESP32 → Arduino protocol.
- Missing / stale sensors are invalid, never substituted with fabricated healthy values.
- Firmware target builds and hardware tests are separate: report exactly which were run.

## Next milestone
Implement a read-only hardware telemetry adapter and its parser / timeout tests after confirming the actual board and UART pin assignments. Preserve the runnable simulation throughout.
