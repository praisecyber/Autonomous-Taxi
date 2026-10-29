# Backend

`taxi/` contains the Python API, authentication, simulator and storage. `tests/` contains
the Python tests. Install from the repository root with
`.venv/bin/python -m pip install -e '.[dev]'`, then run `.venv/bin/python -m taxi` there.
The API listens on loopback port 8000; it does not serve UI pages or assets.

Run the separate frontend with `node frontend/server.mjs` in another terminal.
Keep `.env` and runtime data at the repository root. Dependencies stay in the root
pyproject.toml. See [full startup/API guide](../docs/FRONTEND-BACKEND.md).
