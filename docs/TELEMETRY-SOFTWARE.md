# Simulation telemetry validation — Member 4 software

The shared `frontend/public/telemetry.js` contract is used by all five interfaces
through `shared.js`. WebSockets are read-only; this module never sends commands.
It processes each received message immediately without keeping a message history.
This does not bound the browser/network's internal receive buffer or implement the
future backend frame queue; Member 2's bounded backend interface work remains open.

## Validation contract

A message must be JSON text of at most 65,536 JavaScript string characters, containing
an object with:

- `mode: simulation`, a known vehicle state and `motor_output_enabled: false`;
- finite nonnegative speed, finite x/y position, a known stop or null;
- null/string reason (at most 256 characters) and a nonnegative safe-integer sequence;
- a route of at most four known map node IDs;
- a null trip or an object with a bounded nonempty ID, known terminal/active status,
  and known origin/destination stop IDs;
- telemetry source `simulated`, explicit boolean obstacle/sensor_failed/link_failed,
  and finite nonnegative sensor/link age values.

Unknown or missing critical fields, stringified booleans, nonfinite numbers, unexpected
sources and oversized messages are invalid; no healthy defaults are substituted.
Validly structured telemetry can still report stale/failed inputs. Sensor/link health
requires explicit false failure flags and ages no greater than 0.50 seconds. This
is the existing simulation limit, not a measured device threshold.

## Transport behavior

Until a valid snapshot arrives, reconnect stays disconnected. Invalid messages
immediately mark telemetry stale/invalid without replacing the last accepted data.
No valid message for 1.5 seconds marks it stale. Closed sockets mark disconnected;
reconnect waits 1.8 seconds and never issues start/rearm/reset. Messages from obsolete
sockets are ignored. Page cleanup cancels retry and silence timers. A fresh valid
FAULT snapshot stays FAULT; reconnect does not clear server state.

The backend's `sequence` is a motion-update count, not a heartbeat or capture-time
clock. It can remain unchanged while stopped. This contract does not claim replay
protection, capture-age verification or validation of actual device measurements.
Source timestamps and backend latest-frame queues remain future Member 2 contract work.

## Reproduce

```bash
node --test frontend/tests/*.test.mjs
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium --screenshots /tmp/member4-telemetry-review --axe /tmp/taxi-axe/axe.min.js
```

Use a verified axe distribution or omit that optional argument. The Node suite uses
a deterministic clock and simulated WebSockets: missing/malformed/oversized data,
reported age/failure, silence, reconnect, obsolete sockets and cleanup are covered.
The browser runner additionally injects a real-schema snapshot with its failure flag
removed and checks that recovery controls stay disabled and speed becomes unavailable.
No real accounts are modified. Physical tests are outside this assignment.

Validation on 30 October 2026: six Node tests passed (five telemetry scenarios plus
frontend proxy integration), 51 backend tests passed, Ruff and browser JS syntax
checks passed. Chromium passed the connected workflows and missing-failure-flag
injection with no JavaScript errors; axe found zero WCAG 2.1 A/AA violations in the
tested desktop/phone views. Screenshots: `/tmp/member4-telemetry-review` (local,
untracked). One upstream Starlette/httpx deprecation warning remains. This evidence
does not establish native Windows/LAN rollout or human team acceptance.
