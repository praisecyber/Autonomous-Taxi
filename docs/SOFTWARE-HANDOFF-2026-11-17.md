# Software handoff — 17 November 2026

Scope: four interfaces, backend simulation, accounts/configuration, diagnostics,
software perception input seam and Windows-PC/LAN deployment tooling. Render is
not used. No hardware/firmware/physical-control task is included.

## Member 1 — passenger

Technical handoff is implemented and reproduced by the browser runner: phone/desktop
booking, matching simulated arrival, owned-trip cancellation, role rejection,
stale/invalid/disconnected states and retained history. Ownership and double-booking
restrictions are also covered by backend tests. Screenshots are under
`/tmp/taxi-final-review-20261117` in this workspace. Human teammate acceptance and
actual phone/LAN checks are still to be recorded; no teammate sign-off is invented.

## Member 2 — operator, mission and backend input seam

One supervisor retains mission/fault/terminal-state rules. AI/perception experiments
remain in the backend and are not represented as validated autonomous driving.
`backend/taxi/latest_frame.py` provides a tested, thread-safe one-slot software frame
input interface. Immutable payloads are capped at 1 MiB; newer valid input replaces
older input. Simulated/recorded frames require strictly increasing producer sequences
and captured times in the host monotonic domain. Invalid, replayed, future, expired
or oversized input becomes unavailable. A slow consumer cannot accumulate a frame
queue in this object. It is an interface, not a connected camera/codec/inference engine.

Snapshot and sample timestamps are now explicit. The browser verifies consistency
with reported ages; no cross-device wall-clock synchronization is assumed. Motion
sequence remains a motion count, not a heartbeat. See [telemetry contract](TELEMETRY-SOFTWARE.md).

## Member 3 — admin, accounts and PC operations

Role/ownership, admin records, reporting and version/state configuration checks
remain covered by backend/browser tests. Windows/Linux PC launcher, explicit LAN
HTTPS binding, local CA trust instructions, private checkpoint receipts and optional
current-user Windows task registration are prepared. Linux startup/readiness/shutdown
was checked on an isolated restored database.

This resumed cloud workspace has no earlier `runtime/taxi.sqlite3` or credential
files. No replacement real accounts/passwords were created. Preserve/restore the
original protected data on the Windows PC. Privately delivering the existing user
credentials and each user's live password rotation remain user/team actions.

The fresh recovery evidence uses a **disposable simulation fixture**, not the missing
real database: five generated test accounts, a passenger-owned completed trip and
version-3 persisted configuration. SQLite integrity/FK, history/ownership/configuration
retention, HTTPS/WSS, forced rotation, role/configuration gates and five copied-session
revocations are exercised. Private fixture/report files stay outside Git at
`/tmp/taxi-final-operations-20261117/final-drill/`.

## Member 4 — diagnostics and telemetry validation

Strict schema/boolean/source/finite-number/message-size checks, sample-age consistency,
silence timers, stale inputs, malformed messages, reconnect, obsolete sockets and
cleanup have deterministic Node tests. The browser injection test removes a failure
flag and verifies invalid state, unavailable speed and disabled recovery controls.
Server role tests reject private history/events/configuration and operator commands
for diagnostics users. No mutation is sent by the telemetry watcher.

## Reproduce software verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
node --test frontend/tests/*.test.mjs
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium --screenshots /tmp/taxi-final-review-20261117 --axe /tmp/taxi-qa/node_modules/axe-core/axe.min.js
```

The optional axe file must be a verified local distribution. CI now runs all Node
telemetry/proxy tests, a separate Chromium/axe job and a Windows-PC job covering
launcher configuration, backup ACL tests and task-script parsing. Local Linux
results do not prove those new Windows/GitHub jobs have passed. GitHub API access
returned Forbidden here; remote run status is unverified. Windows-specific tests
are skipped locally when their platform is unavailable.

## Remaining steps on the actual Windows PC

1. Restore the original database/credentials privately; do not silently provision
   replacement accounts. Have each user rotate their own password.
2. Inspect the PC LAN adapter/IP, install the verified Windows Caddy executable and
   run the Python launcher with that explicit private address.
3. Verify Windows ACLs, narrowly scoped firewall access and client public-CA trust.
   Open the HTTPS origin from an actual phone/teammate PC and run the joint flow.
4. Test task registration with `-WhatIf`, then register only the selected sign-in
   and daily backup schedule. Verify LastRunTime/LastTaskResult and receipts.
5. Select a separate encrypted backup destination/recovery owner, transfer a checkpoint
   privately and verify a restore from that destination. Same-disk copies do not
   establish disk-loss recovery. No automatic pruning or external transfer is enabled.

Follow [PC server guide](../deploy/PC-SERVER.md). Names, deadlines, external storage,
actual Windows/network behavior and human acceptance require facts/actions outside
this cloud workspace. These are deployment/handoff items, not missing simulated UI
features. No public hosting or router forwarding is configured.

## Recorded local results

- Backend: **65 passed, 1 Windows-only test skipped**, one upstream Starlette/httpx
  deprecation warning. Ruff passed.
- Frontend: **7 Node tests passed**; first-party JavaScript syntax checks passed.
- Chromium/axe: connected desktop/phone workflows passed, no JavaScript errors,
  zero detected WCAG 2.1 A/AA violations in tested views. Eighteen viewport captures
  plus full screenshots are available at the local screenshot directory above.
- PC launcher: isolated Linux preflight/startup, verified CA/hostname/readiness and
  shutdown passed; all three listeners stopped. Native Windows remains pending.
- Recovery: five disposable accounts, one passenger-owned completed trip and
  persisted version-3 configuration retained; five copied sessions revoked on
  second restore; source fixture remained byte-for-byte unchanged. Backup SHA-256:
  `c69489099782eff93c2ad0463a8dd3f70d4d96c5e835b17bf479033142b19d50`.

No real credential or private key is included in this document or committed files.
