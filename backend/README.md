# Backend

`taxi/` contains the Python API, authentication, simulator and storage. `tests/` contains
the Python tests. Install from the repository root with
`.venv/bin/python -m pip install -e '.[dev]'`, then run `.venv/bin/python -m taxi` there.
The API listens on loopback port 8000; product UI pages/assets stay in the frontend.
Swagger API documentation is served at `/docs` with locally bundled assets.

Run the separate frontend with `node frontend/server.mjs` in another terminal.
Keep `.env` and runtime data at the repository root. Dependencies stay in the root
pyproject.toml. See [full startup/API guide](../docs/FRONTEND-BACKEND.md).

## Backend-owned brain

All vehicle decision/perception code stays on this side of the API:

- `taxi/supervisor.py`: mission state, simulated movement and latched fault handling.
- `taxi/navigation.py`: route planning and configured virtual stops.
- `taxi/configuration.py`: validated route/stop configuration.
- `taxi/perception/`: experimental Python perception/benchmark scripts and model weights.
- `vendor/YOLOX`: the pre-existing third-party Git reference, moved from the repository root.

The frontend contains no model files, inference code, planner or vehicle supervisor.
It sends authorized HTTP requests and displays read-only WebSocket results. The API is
the boundary; one backend supervisor owns the vehicle state.

The normal runnable brain is the deterministic simulation. YOLOX is an uninitialized
legacy Git reference without a submodule URL in this repository; it is not automatically
installed or loaded. The experimental perception scripts need their separately validated
ML/camera environment and are not wired into mission authority. Their old experimental
vehicle alert endpoints are not part of the current API. No real camera inference or
physical movement is claimed by the standard setup.
