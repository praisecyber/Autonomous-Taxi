# Member 1/2/3 technical integration review — 29 October 2026

Base reviewed: main `97aa432`. This is a code/integration review and is not a claim that
individual team members have signed off.

## Findings resolved

1. The Member 2 prototypes imported removed supervisor classes and instantiated separate
   controllers. Workstream routers now use `request.app.state.core` from the canonical
   factory. Root `api:app` uses that factory too; one worker owns one supervisor.
2. The old standalone operator page used obsolete unauthenticated endpoints, hard-coded
   stop/trip identities and a misleading physical emergency-stop label. It now redirects
   to `/operator`, the tested dashboard with account/legacy operator authorization.
3. Updated stop labels reached the selector but not the map. Both now render configured
   names as text. Chromium verifies a renamed Library appears after reload.

## Contracts verified

- Passenger booking aliases derive ownership from the session, reject supplied identity
  fields, and hide foreign/unowned legacy trips on read, list, cancellation and telemetry.
- Passenger and admin sessions cannot issue operator start/stop/rearm/reset/hazard controls.
  Operator sessions do not grant admin account/configuration authority.
- Configurations use optimistic versions, fixed node geometry, valid mapped road segments
  and connected bidirectional routes. Active/faulted missions reject updates without
  changing their route or clearing faults. No automatic resume endpoint remains.
- Legacy histories survive schema migration, sessions expire/revoke, and restore revokes
  copied sessions and interrupts active trips.

## Validation

33 pytest tests passed on Python 3.12; Ruff and all four browser script syntax checks
passed. Chromium passed account creation/revocation, passenger booking/cancellation,
operator session controls at `/operator`, reporting/pagination, text-safe event detail,
configuration gates/save, renamed labels, sign-out and desktop/mobile checks. One upstream
Starlette/httpx deprecation warning remains. Production deployment and hardware behavior
were not tested.

The environment proxy rejects CONNECT requests to `api.github.com` with HTTP 403, so the
GitHub PR/merge API is unavailable. Git fetch/push use the existing supported GitHub proxy.
The user authorized the main-branch merge. No environment configuration was published.
