# Four-interface frontend completion and review

Reviewed on 29 October 2026. This completes the current simulation interfaces; it does
not claim physical vehicle, firmware, camera or production deployment validation.

## Screens

| Route | Purpose | Data and authorization |
|---|---|---|
| `/passenger` | Choose a destination; request/cancel an owned trip; follow progress and arrival | Passenger account; owner-scoped API records and telemetry |
| `/operator` (also `/`) | Read vehicle state/map; start, stop, rearm/reset; inject simulation faults | Operator session or explicitly permitted local demo token |
| `/admin` | Find paginated records, manage users/access, view reports and edit permitted stop names | Administrator session; versioned configuration and mission-state checks |
| `/diagnostics` | Identify fresh, stale, invalid and missing information | Read-only simulated status; hardware information stays unavailable |
| `/account` | Shared sign-in, workspace access, password change and sign-out | Backend-issued session and role; no separate frontend identity system |

Navigation, typography, form errors, focus rings, spacing, panels, tables, button states,
status labels and responsive layouts are shared through `frontend/public/shared.css`.
`shared.js` supplies navigation, text/icon status badges, map rendering and telemetry
freshness/reconnect handling. `api-client.js` handles same-origin requests and errors;
no credentials are saved in browser storage.

## Palette

| Token | Color |
|---|---|
| Background / black | `#080D0A` |
| Surface | `#122019` |
| Primary / green | `#22C55E` |
| Highlight / yellow | `#FACC15` |
| Main text | `#F5F7F5` |
| Muted text | `#A7B5AC` |

Green and yellow buttons use the background black for text. All state indicators pair
words and icons: Ready, Active, Stopped, Fault, Disconnected, plus explicit Stale messages.
Stored terminal status codes remain distinguishable in badges and record detail.
Stop is a separate labelled yellow software action. On phones it remains visible in a
bottom action panel; it is never labelled as a physical emergency stop.

## Freshness, privacy and valid claims

- A WebSocket connection alone is not live telemetry. The UI waits for a valid snapshot.
  No message for 1.5 seconds marks telemetry stale; closed sockets mark it disconnected.
  Invalid snapshots also invalidate the display. Unknown speed/age/current-stop fields
  become Unavailable, and retained map positions are labelled as last known.
- Start, rearm/reset and input controls require current telemetry and permitted authority.
  An authorized software Stop can still be requested when telemetry is unavailable;
  no request silently retries a mutation. Reconnect never issues rearm or start.
- Sensor/link validity uses the existing **simulation-only** 0.50-second freshness limits.
  These are not measured physical safety limits.
- Passenger progress uses the configured route and current simulated position. Confirmed
  arrival requires the matching owned trip to be COMPLETED at zero simulated speed.
  Stale/disconnected progress is unavailable; historical trip status is labelled as stored.
- Diagnostic sensor/link samples are labelled simulated. Camera, boards, UART, measured
  obstacle distance and physical sensor feedback remain Unavailable. A latched fault is
  shown independently of whether simulated samples have resumed updating.
- Admin reports count actual records. Tables and reports identify their data as stored
  snapshots rather than live vehicle telemetry. Stop names have labelled inputs; advanced
  JSON remains available. Backend version/state/graph validation is unchanged.

## Evidence

- **34 backend tests passed**, preserving authentication, ownership, mission and fault rules.
  One upstream Starlette/httpx deprecation warning remains.
- Node frontend/proxy tests, first-party JavaScript syntax checks and Ruff passed.
- Chromium exercised actual frontend/backend processes: login, booking, cancellation,
  matching-trip arrival, role rejection, user revocation, record pagination/filtering,
  configuration save/gates, operator Stop including the phone action, and fault injection.
- WebSocket tests withheld, corrupted and disconnected telemetry, then reconnected.
  Controls/progress became unavailable; a latched fault stayed faulted after reconnect.
- Layout checks covered **1440, 768, 390 and 360 px** without document overflow. Tables
  scroll within named keyboard-focusable regions. Phone maps include readable stop legends.
  Visual screenshots were reviewed for operator, passenger, admin, diagnostics and account.
- Keyboard checks verified the visible skip link, focus indicator and main-content target;
  native radio/forms and explicit inline errors were exercised.
- **axe-core 4.14.0 detected zero WCAG 2.1 A/AA violations** across 18 desktop/phone audits:
  passenger stored/arrived/stale views, operator ready/fault/stale views, diagnostics,
  account and admin. This is bounded automated evidence, not accessibility certification
  or an exhaustive assistive-technology/user study.

Reproduce the integration and optional accessibility checks:

```bash
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium --screenshots /tmp/taxi-ui-review
# To include axe, supply a verified local axe-core distribution:
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium --screenshots /tmp/taxi-ui-review --axe /path/to/axe.min.js
```

Screenshots are generated outside Git. No real users or passwords are created by the
check; its temporary database and test servers are removed after the run.
