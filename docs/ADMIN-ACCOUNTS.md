# Member 3: accounts, ownership and administration

Developed on `feature/admin-interface`; technical integration review is recorded below.
Human team sign-off is separate from the automated checks.
No real account credentials are bundled. The shared operator token is not an admin credential.

## First administrator and local startup

1. Stop the single taxi server. Preserve existing runtime data; do not delete it.
2. Install dependencies: `.venv/bin/python -m pip install -e '.[dev]'`.
3. Back up an existing database before migration:
   `.venv/bin/python -m taxi.manage backup --source runtime/taxi.sqlite3 --output runtime/backups/before-accounts.sqlite3`.
   Choose a new output name if it exists. Skip only when there is no database yet.
4. Run `.venv/bin/python -m taxi.manage create-admin --username your-admin-name`.
   Enter and confirm a 12–128 character password at hidden prompts. Do not put passwords
   in shell arguments, source files or chat. Usernames use 3–64 ASCII letters, digits,
   underscores, periods or hyphens, starting with a letter/digit. They are case-insensitive.
5. Start `.venv/bin/python -m taxi`. Sign in through `/admin`. Create passenger, operator
   or further administrator accounts and convey their initial credentials privately.
   Users can change their passwords at `/account`.

The bootstrap command refuses while an enabled administrator exists. Use authenticated
administration to create more admins. There is no password-reset email service or default
recovery credential. Keep an additional trusted admin and a protected backup.

`TAXI_DATA_DIR` selects the application's data directory. The CLI's default database is
`runtime/taxi.sqlite3`; if using another data directory, pass its full database path with
`create-admin --database ...` and explicit backup/restore source/output paths.

## Access contract for Members 1 and 2

| Capability | Passenger | Operator | Admin | Unauthenticated |
|---|---|---|---|---|
| Health, configured stops, simulated position | Yes | Yes | Yes | Yes |
| Start simulated trip | Own identity | Unowned operator trip | No | No |
| List/read trips | Own only | All | All | No |
| Cancel trip | Own active only | Any active | No | No |
| Stop/rearm/reset/inject faults | No | Yes | No | No |
| Read event log | No | Yes | Yes | No |
| Paginated records and reports | No | No | Yes | No |
| Manage accounts/configuration | No | No | Yes | No |

Administrators do not inherit vehicle command authority. Another admin must change your
own access; there is no delete-user endpoint, preserving historical owner references.
Changing role/enabled state revokes all of the target user's sessions. Keep an enabled
admin. Passengers cannot claim a different owner: the trip POST accepts destination only.
Legacy and operator-originated trips retain a null owner and are not exposed to passengers.
Foreign trip IDs return 404 for both read and cancel. Terminal trips cannot be cancelled again.

Session requests:

1. `POST /api/auth/login` with JSON `{ "username": "...", "password": "..." }`.
   Success sets an HttpOnly, SameSite=Strict cookie and returns `{user, csrf_token}`.
2. Use same-origin cookies (`credentials: 'same-origin'`). `GET /api/auth/me` restores
   the current identity/CSRF token on reload. Do not store passwords or session tokens
   in localStorage/sessionStorage. The browser manages the HttpOnly cookie.
3. Include `X-Taxi-CSRF: <csrf_token>` on every cookie-authenticated mutation. A foreign
   Origin is rejected. No permissive CORS configuration is installed.
4. `POST /api/trips` with destination only, then use the returned trip ID for read/cancel.
   `GET /api/trips` is an array capped at the latest 100 accessible records.
5. `POST /api/auth/logout` revokes the current session. Password change through
   `POST /api/auth/password` takes `current_password` and `new_password`, revokes every
   session for that account and requires sign-in again.

401 means missing/expired/invalid authentication; 403 means a role/CSRF/origin restriction;
404 hides inaccessible trip IDs; 409 means an incompatible state, duplicate account or
stale configuration version; 422 means invalid input; 429 limits repeated login attempts.
Validation responses omit input values, including invalid passwords.

Public status and telemetry omit the active trip record. Cookie-authenticated passengers
see it only when they own it. Operator/admin sessions can see it; owner IDs are omitted
from telemetry. WebSockets recheck sessions for every message, so expiry/revocation
removes the trip record without waiting for reconnection. Public simulation position,
route and sensor information remain available; this is not a private fleet deployment.

Member 1 should reuse the `/account` login/session contract rather than another auth
system. The small passenger section there demonstrates booking and ownership; a dedicated
passenger interface can replace it. Member 2's existing dashboard now uses an operator
session automatically and loads configured stop labels. Original token headers still work
in explicit demo mode, but never grant administrator access.

## Security choices and limits

- Passwords use `pwdlib[argon2]` and its recommended Argon2id implementation (`argon2-cffi`).
  This maintains a standard library-backed password format instead of custom cryptography.
  The tested versions are pwdlib 0.3.1 and argon2-cffi 25.1.0. Both are dependencies declared
  through pyproject.toml. Password verification/hashing runs off the supervisor event loop.
- Sessions are random 256-bit opaque tokens. Only SHA-256 token hashes are stored in SQLite.
  Fixed maximum lifetime is eight hours; logout, disablement, role/password changes and
  restore revoke applicable sessions. No browser storage holds the tokens.
- Login limits are per direct client IP, ten attempts per five minutes, in this one process.
  Successful attempts count too. The limiter resets on restart; no distributed deployment,
  reverse-proxy IP trust, MFA or email/password recovery is implemented.
- `TAXI_ALLOW_LEGACY_TOKEN=auto` enables the shared-token demo only before any accounts exist
  at startup. `0` always disables it. `1` explicitly enables operator access by shared token
  even when accounts exist: local demo only. An invalid explicit bearer header never falls
  back to a valid cookie. Account sign-in clears the dashboard's legacy token field.
- `TAXI_SECURE_COOKIES=0` supports local loopback HTTP. Use `1` with HTTPS before sharing.
  TLS termination, deployment host/proxy configuration and a production security review
  remain separate work. Keep the single-worker, single-supervisor constraint.
- Record details render as text, not HTML. Private API responses are `Cache-Control: no-store`.
  Backups contain password hashes and personal records; protect them like the live database.

## Configuration contract proposed for Member 2 review

`GET /api/admin/configuration` returns `{version, stops, edges}`. PUT the complete object
with the current version. Stale versions return 409. Changes persist in SQLite and the
supervisor uses them immediately for subsequent trips and after restart.

Updates are accepted only with READY at A, no current trip and no active mission. The
operator must explicitly reset a stopped/completed/faulted simulator first. An admin
cannot clear faults or reset through this configuration API. There is no await between
validation, state check, persistence and in-memory assignment.

Existing stop/node IDs and map coordinates remain fixed. Labels are validated, road
segments must be existing mapped segments, bidirectional and duplicate-free, and every
node must remain reachable. The baseline graph is a tree, so removing any of its roads
is rejected. This deliberately supports validated names and verification of the current
route graph; adding roads or changing geometry requires Member 2's planner/map review.
Operators should reload the dashboard after configuration changes. Physical routes and
hardware thresholds are outside this API.

## Reports, pagination and schema migration

- `/api/admin/records/trips` and `/api/admin/records/events`: `{items,total,limit,offset}`.
  Defaults: 25 rows; maximum 100. `q` is a literal substring search, with `status` or
  `event_kind` as exact filters. Queries use bound SQL values. Trip ordering is created
  time then ID descending; event ordering is ID descending. Offset pagination is a live
  view of stored data and can shift when new records arrive; it is not an export snapshot.
- `/api/admin/users` uses the same paging envelope. Reports at `/api/admin/reports` group
  all actual stored trip statuses and event kinds, not just a displayed page.
- `PRAGMA user_version=1` adds users, session hashes, persisted configuration and nullable
  `trips.owner_id`, with a foreign key and ownership index. Legacy version-0 data is retained;
  no owner is invented for old history. Schema changes run in a transaction. Newer database
  versions are refused. A backup is the rollback path; no lossy down migration is supplied.
- Normal startup marks ACTIVE trips INTERRUPTED, preserving terminal statuses. CLI
  bootstrap does not run startup recovery. No database copy resumes a physical mission.

## Backup and restore procedure

Stop the server before offline administration. Both commands require a new output path
and never overwrite a live database. Example:

```bash
.venv/bin/python -m taxi.manage backup --source runtime/taxi.sqlite3 --output runtime/backups/checkpoint.sqlite3
.venv/bin/python -m taxi.manage restore --source runtime/backups/checkpoint.sqlite3 --output runtime/restore-check/taxi.sqlite3
```

The SQLite backup API captures a consistent database, including committed WAL data.
Integrity, foreign keys and supported schema versions are checked. Restore migrates the
copy, revokes all sessions and interrupts active trips. It adds a restore audit event.
Copies are published atomically with private file permissions. Keep outputs under ignored
runtime paths or outside the checkout; never commit database copies.

Validate a restored copy before selecting it for normal operation:

```bash
TAXI_DATA_DIR=runtime/restore-check .venv/bin/python -m taxi
```

Sign in again, inspect reports/history and run a fresh simulated trip. Stop the validation
server afterward. Preserve the original database and backup; select the intended data
directory explicitly rather than overwriting or deleting either. Backups/retention and
actual off-machine recovery remain the service owner's operational responsibility.

## Integration review against Member 2 main branch (29 October 2026)

The review integrated main at `97aa432` and replaced disconnected prototype entry points
with shared application-owned state. `taxi/routers/passenger.py` owns trip endpoints;
`taxi/routers/operator.py` owns role-gated mission commands; `taxi/routers/admin.py` exposes
account/admin routes. None instantiate a supervisor. `/operator` serves the working
dashboard, and the old standalone operator page redirects there. `uvicorn api:app` now
uses the same canonical app factory as `python -m taxi`.

`POST /api/passenger/book` is an alias of `/api/trips`: JSON contains `destination` only,
using configured stop IDs A/B/C. `POST /api/operator/start` takes the same destination-only
payload and requires operator authority. Old prototype `start_node`, `destination_node`,
`operator_id` and hard-coded trip IDs are not an authentication or routing contract.
Use `/ws/telemetry` for read-only updates; it never advances movement. The supervisor
loop alone advances the simulation. Removed prototype `/api/vehicle/clear` auto-resume
behavior is not available; clearing simulated hazards never rearms a fault.

Configuration labels update both the operator destination selector and SVG map on reload.
New tests confirm that both workstream aliases share one supervisor, passenger IDs are
owner-scoped, operator start rejects passenger/admin sessions, and faulted/active missions
reject configuration changes without changing their path or clearing the fault. This is a
technical integration review; it does not claim personal approval from team members.
