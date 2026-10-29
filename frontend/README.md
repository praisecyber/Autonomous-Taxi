# Frontend

HTML, CSS and browser JavaScript live in `public/`. Run `node frontend/server.mjs` from
the repository root with Node.js 22+; no npm installation is needed. Start the Python
backend separately with `.venv/bin/python -m taxi`.

The browser uses relative `/api` and `/ws` requests, which this local server forwards to
the backend on port 8000. Pages are served on port 3000. No database or application state
is owned here. See [full startup/API guide](../docs/FRONTEND-BACKEND.md).

The four workspaces are `/passenger`, `/operator`, `/admin` and `/diagnostics`; `/account`
provides shared sign-in. Design tokens/components live in `public/shared.css`, while
`shared.js` owns navigation and telemetry freshness. See [UI review](../docs/FRONTEND-REVIEW.md).
