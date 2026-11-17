# Autonomous Taxi — software-only team checklist

Updated 17 November 2026. This is the current assignment plan and supersedes older
hardware assignments in previous versions of this document. The project PC hosts
the service; Render is not used. Names and deadlines still need team confirmation. The uploaded plan specifies
Windows PC hosting with phones/computers on the local network; see [source alignment](PLAN-ALIGNMENT.md). No physical-device work is assigned here.

Current consolidated evidence: [17 November software handoff](SOFTWARE-HANDOFF-2026-11-17.md). Technical completion is separate from human acceptance and native Windows/LAN rollout.

## Reviewed software baseline

- [x] Four connected simulation interfaces with shared black/green/yellow design.
- [x] Passenger ownership, operator commands, administrator accounts/records/configuration and read-only diagnostics permissions.
- [x] Single backend supervisor, terminal trip history, latched faults and explicit recovery.
- [x] Local HTTPS profile, account rotation support and isolated backup/restore drill.
- [x] 43 backend tests, lint, proxy tests and Chromium/axe checks recorded in the [merge review](MERGE-REVIEW.md) and [Member 3 handoff](MEMBER3-SOFTWARE-HANDOFF.md).

These are technical review results, not evidence that each member has completed a
human handoff. Simulation and recorded fixtures must be labelled as such.

## Member 1 — Passenger · probix.member1

Existing booking/progress/cancellation and identity integration are implemented.

- [x] **P1-06 technical handoff** — Automated phone/desktop demonstration of booking, matching arrival and owned cancellation; [fresh evidence](SOFTWARE-HANDOFF-2026-11-17.md).
- [ ] Record human Member 1/2 acceptance and actual phone/LAN demonstration.
- [x] Verify busy/invalid requests, duplicate-mission rejection, stale/disconnected data and cross-passenger denial — backend/browser tests.
- [x] Link local screenshots, automated walkthrough and test evidence — [handoff](SOFTWARE-HANDOFF-2026-11-17.md).
- [ ] Review current remote CI and record manual team results; remote CI API is unavailable here.

Complete when Member 2 can reproduce a passenger-originated simulated mission.
Use the shared session API; do not create a second auth system.
Evidence: [frontend review](FRONTEND-REVIEW.md), [account contract](ADMIN-ACCOUNTS.md).

## Member 2 — Operator / mission / backend AI · probix.member2

Existing operator interface, routers and mission guards are implemented.

- [x] **P2-05: software interface seam** — Define bounded latest-frame/telemetry inputs: source, timestamps, validity, maximum age and malformed/missing behavior.
- [x] Implement deterministic simulation/recorded-fixture tests for stale data, replay/future rejection and a one-frame bounded buffer — [contract](TELEMETRY-SOFTWARE.md).
- [x] Keep perception/AI logic in the backend; document the software seam separately from optional inference/codec/device work.
- [x] Reproduce the joint software demo and technically review timestamp/parser/fault behavior — [handoff](SOFTWARE-HANDOFF-2026-11-17.md).
- [ ] Obtain the human integration lead's acceptance.

Preserve one supervisor/worker, one active trip, terminal states, fault latching and
explicit recovery. Reconnect never authorizes a command.
Evidence: [architecture](ARCHITECTURE.md), [integration review](INTEGRATION-REVIEW.md).

## Member 3 — Admin / accounts / PC operations · probix.member3

Accounts, permissions, reports, configuration validation and restore tooling are implemented.

- [x] Inspect configured roles and verify forced rotation on isolated copies.
- [x] Prepare individual private credential files and checkpoint backup command.
- [x] Verify admin browser flows, configuration restrictions and fresh HTTPS/restore drill.
- [ ] Privately deliver each person's credential entry and obtain assignment acknowledgement.
- [ ] Have each person rotate their live password; never infer completion from a copy test.
- [x] Establish intended Windows PC / local-network access from the uploaded plan.
- [x] Provide cross-platform PC launcher and explicit LAN HTTPS configuration; 49 backend tests and Linux HTTPS/shutdown checks passed.
- [ ] Inspect actual Windows PC network details, test native startup and complete firewall/client-trust setup.
- [x] Prepare optional current-user Windows sign-in/daily-backup task helper with preview; Windows execution remains unverified.
- [ ] Test native task/ACL behavior on the PC, select encrypted separate backup storage and recovery owner, then enable the chosen daily schedule.

Evidence/runbook: [Member 3 software handoff](MEMBER3-SOFTWARE-HANDOFF.md),
[PC server guide](../deploy/PC-SERVER.md). No public domain is required for same-PC use.

## Member 4 — Diagnostics / telemetry validation · probix.member4

The existing diagnostics interface labels simulation and missing information.

- [x] Add deterministic fresh/stale/missing/malformed/disconnected WebSocket fixtures — [software telemetry evidence](TELEMETRY-SOFTWARE.md).
- [x] Timestamp and backend buffer contract technically reviewed with deterministic tests — [contract](TELEMETRY-SOFTWARE.md). Human Member 2 acceptance remains separate.
- [x] Bound frontend message size and validate schema, explicit failure flags, reported ages and transport silence — [contract/tests](TELEMETRY-SOFTWARE.md).
- [x] Add backend monotonic snapshot/sample timestamps and browser age-consistency checks; motion sequence remains separate.
- [x] Test silence, stale reported samples, malformed messages and WebSocket disconnect/reconnect — deterministic Node and browser checks.
- [x] Verify FAULT is retained on reconnect and invalid/stale displays stay unavailable until valid data arrives — [browser runner](../scripts/check_admin_browser.py).
- [x] Verify diagnostics cannot read private history/events/configuration or issue operator commands — backend role regression.
- [x] Link phone/desktop screenshot locations, parser/freshness/fault results and reconnect walkthrough — [fresh handoff](SOFTWARE-HANDOFF-2026-11-17.md).

Complete when deterministic fixtures reproduce each condition without fabricated healthy
values or hidden commands. No hardware confirmation, wiring, board builds, motor control
or physical tests are assigned. Historical hardware notes remain reference material only.

## Joint software demonstration

1. Sign in with separate test identities; rotate temporary credentials first.
2. Member 1 books one simulated trip; Member 2 monitors the matching mission.
3. Member 4 verifies source/state/freshness without gaining private-trip permissions.
4. Member 3 finds the stored record and demonstrates role/configuration restrictions.
5. Use separate trips to demonstrate arrival and cancellation; simulate disconnect/fault/reconnect.
6. Record expected/actual results, known gaps and review links before checking off tasks.

## Shared delivery rules

Use `frontend/public/shared.css`, `shared.js` and `api-client.js`. Preserve the existing
palette, accessible focus/form errors, status words/icons and desktop/phone layouts.
Backend code lives in `backend/taxi`; no second supervisor or permissive CORS.
Run appropriate pytest/Ruff/JS/browser checks for changes. Keep credentials, databases,
private CA keys and generated backups out of Git. Each member uses a feature branch
and links reviewed evidence. No payment/fleet expansion is assigned in this plan.

Private-data availability note: this resumed workspace has no earlier runtime database/credentials. Fresh November operational evidence uses disposable fixtures only. Preserve/restore original data on the PC; do not recreate real accounts based on this document.
