# Swagger API explorer

Start the backend and frontend as documented in [frontend/backend setup](FRONTEND-BACKEND.md).
Open `/docs` on frontend port 3000, or on backend port 8000. The machine-readable schema
is `/openapi.json`. The frontend already forwards these paths to the API.

The explorer groups endpoints into Status, Accounts, Trips, Operator and Administration.
Expand an endpoint, click **Try it out**, enter its request fields and click **Execute**.
The listed API calls use the same backend authorization and mission rules as the UI.

## Account sessions

1. Expand Accounts → `POST /api/auth/login`.
2. Click Try it out, supply your existing username/password and Execute.
3. Use endpoints permitted for that role. The browser keeps the HttpOnly session cookie;
   Swagger obtains the CSRF token from `/api/auth/me` and sends `X-Taxi-CSRF` automatically
   for session-authenticated mutations.
4. Use `POST /api/auth/logout` to revoke this session. Signing in through `/account` or
   `/admin` on the same host/port also works with Swagger there.

Use login to establish AccountSession; browsers do not let Swagger set an HttpOnly cookie
through the Authorize dialog. Do not switch between localhost and 127.0.0.1 or between
frontend/backend ports in one test flow: session/CSRF requests should use one origin.

Passengers can read/cancel only their own trips. Operators own simulation controls.
Administrators manage accounts, records and settings but cannot issue operator commands.
Configuration updates still require READY at A with no current trip and a matching version.

## Optional local operator token

When legacy-token access is enabled, choose **Authorize → LocalOperatorToken** and enter
the configured token without a Bearer prefix. This grants operator demo access only.
It never grants administrator access and is disabled once accounts exist by default.
Use Logout in the Authorize dialog to clear that header before switching to a session;
an explicit invalid bearer header does not fall back to a valid cookie.

Swagger does not persist bearer authorizations in browser storage. Browser account
cookies retain their normal session lifetime and are revoked by account logout.

## Local assets and packaging

Swagger UI 5.34.0 is pinned under `backend/taxi/docs_assets/`, including its Apache-2.0
LICENSE/NOTICE and verified npm archive integrity in PROVENANCE.md. The backend wheel
includes these documentation assets; no npm installation or external CDN is needed at
runtime. `swagger-init.js` supplies the same-origin session/CSRF integration.

Swagger documents the HTTP API. Read-only telemetry uses `/ws/telemetry`, which Swagger
cannot execute as an HTTP endpoint. All movement remains simulated.
