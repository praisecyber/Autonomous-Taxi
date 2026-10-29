# Frontend

HTML, CSS and browser JavaScript live in `public/`. Run `node frontend/server.mjs` from
the repository root with Node.js 22+; no npm installation is needed. Start the Python
backend separately with `.venv/bin/python -m taxi`.

The browser uses relative `/api` and `/ws` requests, which this local server forwards to
the backend on port 8000. Pages are served on port 3000. No database or application state
is owned here. See [full startup/API guide](../docs/FRONTEND-BACKEND.md).
