# Autonomous Taxi - Shared Team Workspace

Original allocation: **Member 1 Passenger · Member 2 Operator/mission · Member 3 Admin/accounts · Member 4 Diagnostics/hardware**. Everyone owns a frontend interface plus its supporting work.

Names and deadlines are not assigned yet. Fill them in by pull request. This is a shared repository checklist, not an automatic live telemetry or progress system. Only check tasks after evidence is linked and reviewed.

## Current baseline

- [x] Python/FastAPI backend, one operator-style dashboard and A-to-B/C simulation.
- [x] SQLite trips/events, cancellation, fault latching and explicit simulation recovery.
- [x] Reviewed simulation regression evidence: 43 backend tests, Node proxy test and Chromium/axe checks; see [merge review](MERGE-REVIEW.md). Earlier GitHub CI evidence is historical; current remote CI is not asserted here.
- [x] ESP32-CAM/Arduino **bench starter source** added; compile/hardware operation not verified.
- [x] Four separate interfaces and shared green/yellow/black theme — [reviewed frontend evidence](FRONTEND-REVIEW.md) and [merge review](MERGE-REVIEW.md).
- [x] Real accounts, role permissions, ownership and operational restore drill — [operations evidence](PROBIX-OPERATIONS.md).
- [ ] Real device telemetry/perception and physical movement — blocked on Member 4 hardware confirmation; simulation is not hardware evidence.

## Immediate priority — Member 4 hardware confirmation (P4-02)

**Blocks all real vehicle integration.** Member 4 must complete the [hardware confirmation record](HARDWARE.md#priority-1-confirmation-handoff) with exact part models, power/logic levels, pin-to-pin wiring, feedback and independent stop design. Member 2 reviews the communication/control interfaces before any output implementation. No hardware facts are currently confirmed; do not guess pins or enable motors.

Order: P4-02 confirmed wiring → P4-03 disarmed target builds/JPEG/PING/STOP → P4-04 measured read-only telemetry and parser/freshness tests → P4-05 measured local watchdog/disable protection → P4-06 integration. Keep every hardware task unchecked until linked compiler/bench evidence is reviewed.

Other next actions: Member 1 confirms the passenger flow with the team; Member 2 reviews the hardware protocol and preserves simulation; Member 3 privately distributes credentials, confirms member roles and completes public domain/server setup. Names and deadlines still need team assignment. This checklist records technical review, not individual human sign-off.

## Shared design and tools

Frontend: HTML/CSS/JavaScript, SVG, Fetch and WebSocket. Backend: Python/FastAPI/Pydantic, SQLite, pytest and Ruff. Firmware: Arduino C/C++ and PlatformIO/Arduino IDE. No ROS dependency; no mandatory frontend framework migration.

Colours: background `#080D0A`, surface `#122019`, primary green `#22C55E`, highlight yellow `#FACC15`, text `#F5F7F5`, muted `#A7B5AC`. Use black text on bright green/yellow and pair status colours with words.

Shared files now implemented: `frontend/public/shared.css`, `frontend/public/api-client.js` and `frontend/public/shared.js` for navigation, status and telemetry behavior. Member 2 coordinates shared API wiring; Member 3 coordinates auth/schema changes.

## Roadmap and exit gates

| Phase | Status | Owners | Deliverable | Exit gate |
|---|---|---|---|---|
| M0 Foundation | Complete for simulation | All | Existing API, dashboard, simulator, history, tests and GitHub push. | 14 local tests and live simulated A-to-B check passed; GitHub CI succeeded on 3.10/3.12. |
| M1 Shared shell and contracts | Technically complete for simulation | All; Member 2 coordinates | Agree roles and shared UI tokens; create four pages, navigation and workstream routers. | All four pages open, share styling and handle errors; original simulator remains runnable. |
| M2 Connected four-interface simulation | Technically complete; team demonstration pending | 1 + 2 + 3 + 4 | Passenger identity/ownership, mission request, operator supervision, diagnostics and admin record flow. | One authorized passenger trip appears consistently across all screens; access tests pass. |
| M3 Confirmed hardware and read-only telemetry | Blocked by hardware confirmation | 4; reviewed by 2 | Confirm wiring, compile boards, test camera/UART and real sensor drivers; connect read-only adapter. | Real values include source/age/validity; missing or stale values cannot look healthy. |
| M4 Independent local control and stop | Planned; requires M3 | 4 + 2 | Implement tested driver, feedback, watchdog, command freshness and physical disable. | Bench fault tests and measured stopping/disable results recorded before autonomous motion. |
| M5 Perception and localization | Planned; experiments may run earlier | 2 + 4 | Recorded OpenCV marker/path tests, detector benchmark and position tracking between markers. | Required-object/localization performance and latency meet measured project limits. |
| M6 Supervised physical A-to-B trial | Planned; requires M4 + M5 | All | Integrate planner/controller and proven hardware stack on an approved low-speed course. | Reach the defined stopping area, obey route/speed bounds and pass sensor/link/obstacle fault tests. |
| M7 Service and fleet expansion | Later scope | All | Pickup dispatch, boarding sensors, battery, maintenance, accessibility, multi-vehicle and optional payments. | Each feature has an approved scope, required hardware and recorded acceptance evidence. |

## Member 1 - Passenger experience

**Name:** unassigned  |  **Branch:** `feature/passenger-interface`  |  **Interface:** `/passenger`

### Frontend section

Build the destination and booking screen, cancellation button and trip progress. Show loading, rejected requests, stale updates and confirmed arrival.

**Frontend tools:** HTML, CSS, JavaScript, Fetch API, browser WebSocket and shared design tokens.

**Frontend files:** frontend/public/passenger.html and passenger.js (implemented; see FRONTEND-REVIEW.md).

- [x] **P1-01 Build the booking screen** - Show vehicle current stop, destination selector, trip request, cancellation and active-trip card using shared design tokens.
  - Done when: Screen works at phone and desktop widths, with loading, error and disconnected states.
  - PR/evidence: [frontend checks](FRONTEND-REVIEW.md), [ownership tests](../backend/tests/test_accounts.py), [merge review](MERGE-REVIEW.md)
- [x] **P1-02 Connect stops and trip requests** - Reuse configured stop IDs. Send destination only; show a useful error for same stop, invalid stop or busy vehicle.
  - Done when: Exactly one accepted trip is displayed; double-click cannot silently create another active mission.
  - PR/evidence: [frontend checks](FRONTEND-REVIEW.md), [ownership tests](../backend/tests/test_accounts.py), [merge review](MERGE-REVIEW.md)
- [x] **P1-03 Show live trip progress** - Consume read-only telemetry and match it to the active trip ID. Distinguish accepted, active, stopped, faulted and completed.
  - Done when: Arrival appears only when the correct trip is completed and speed is zero.
  - PR/evidence: [frontend checks](FRONTEND-REVIEW.md), [ownership tests](../backend/tests/test_accounts.py), [merge review](MERGE-REVIEW.md)
- [x] **P1-04 Add cancellation** - Request cancellation of the active owned trip and show the server result.
  - Done when: Cancelled trip remains terminal in history; UI never implies physical stopping from request receipt alone.
  - PR/evidence: [frontend checks](FRONTEND-REVIEW.md), [ownership tests](../backend/tests/test_accounts.py), [merge review](MERGE-REVIEW.md)

### Backend section

Integrate the passenger identity/session supplied by Member 3, apply it to passenger requests and cancellation, and test the complete passenger trip flow. Coordinate trip rules with Member 2; do not build a second authentication system.

**Backend tools:** Python, FastAPI, Pydantic and pytest; use Member 3's shared authentication and ownership rules.

**Backend / firmware files:** backend/taxi/routers/passenger.py and backend/tests/test_passenger.py (planned); reuse existing trip APIs.

Backend integration, verification and handoff checklist:

- [x] **P1-05 Integrate passenger identity** - Work with Member 3 on login/session and ownership. Use operator token only in local development.
  - Done when: Passenger cannot use operator/admin controls or read/cancel another passenger trip.
  - PR/evidence: [frontend checks](FRONTEND-REVIEW.md), [ownership tests](../backend/tests/test_accounts.py), [merge review](MERGE-REVIEW.md)
- [ ] **P1-06 Test and hand off** - Add passenger API/UI tests; document manual browser checks; open a pull request.
  - Done when: CI passes and Member 2 can demonstrate a passenger-originated simulated mission.
  - PR/evidence: _add link_

**Dependency:** Needs Member 2 mission-state contract and Member 3 passenger authentication. Do not publish a shared operator token to passengers.

### Layman explanation section

You build the part the passenger uses to ask for a ride. Think of it as the booking counter: the screen asks where the passenger wants to go, and the code behind it sends the request to the right service. It keeps the passenger informed and lets them cancel their own ride. You do not decide how much power the motors receive. Example: someone selects Library and sees the trip progress until arrival is confirmed.

## Member 2 - Operator and mission management

**Name:** unassigned  |  **Branch:** `feature/operator-interface`  |  **Interface:** `/operator`

### Frontend section

Build the operator's route map, active-trip panel, speed/state/fault displays and authorized stop/rearm controls. Keep simulator reset and fault injection clearly labelled.

**Frontend tools:** HTML, CSS, JavaScript, SVG, Fetch API, browser WebSocket and shared design tokens.

**Frontend files:** frontend/public/index.html and app.js serve /operator; operator.html/operator.js redirect older bookmarks.

- [x] **P2-01 Split the operator dashboard** - Move existing map, current mission, state, speed, stop/rearm and simulator controls into its own screen without breaking the demo.
  - Done when: Operator screen preserves the working A-to-B simulation.
  - PR/evidence: [integration contract](INTEGRATION-REVIEW.md), [frontend checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)

### Backend section

Maintain the mission state machine and route planning; coordinate API modules and common payloads. Preserve one active trip, latched faults, explicit recovery and fresh inputs. Prepare interfaces for real perception and telemetry after hardware checks.

**Backend tools:** Python 3.10+, FastAPI, Pydantic, asyncio, route graph, supervisor, pytest, Ruff and GitHub Actions.

**Backend / firmware files:** backend/taxi/supervisor.py, navigation.py and api.py (existing); backend/taxi/routers/operator.py (planned).

Backend integration, verification and handoff checklist:

- [x] **P2-02 Agree shared contracts** - Document trip statuses, role permissions, errors, source labels, freshness and API payloads with the team.
  - Done when: All four interfaces use the same stop/trip IDs and state meanings.
  - PR/evidence: [integration contract](INTEGRATION-REVIEW.md), [frontend checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)
- [x] **P2-03 Integrate team routes** - Coordinate small routers rather than having four people edit api.py independently. Keep one supervisor process.
  - Done when: Four pages and their intended API permissions work together.
  - PR/evidence: [integration contract](INTEGRATION-REVIEW.md), [frontend checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)
- [x] **P2-04 Preserve mission safety rules** - Keep one active mission, terminal cancellation, fault latching and explicit rearm. Reject stale input and timing failures.
  - Done when: Existing regression tests pass; clearing a hazard never resumes a trip.
  - PR/evidence: [integration contract](INTEGRATION-REVIEW.md), [frontend checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)
- [ ] **P2-05 Prepare perception and control seam** - Define bounded latest-frame / telemetry interfaces; later connect real localization and controller only after Member 4 local safety tests.
  - Done when: Old frames cannot build an unbounded backlog; simulator stays available.
  - PR/evidence: _add link_
- [x] **P2-06 Review integration** - Suggested integration-lead role: review shared API/UI changes, run tests and keep main runnable. Assignment remains for team confirmation.
  - Done when: One passenger request can be monitored in operator/diagnostics and found in admin records.
  - PR/evidence: [integration contract](INTEGRATION-REVIEW.md), [frontend checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)

**Dependency:** Needs Member 4 validated device data before real movement and Member 3 authorization rules. Shared control behavior must not bypass Arduino safety.

### Layman explanation section

You build the control room and the trip manager behind it. The operator sees what the taxi is doing, while your code decides whether a trip can start, which approved route to follow and when it must stop. You coordinate the other members' pieces so they behave as one system. Example: if a fault happens during a journey, the screen explains it and the mission remains stopped until the required checks and recovery action are completed.

## Member 3 - Administration, accounts and records

Local implementation is available on `feature/admin-interface`; see
[implementation evidence](ADMIN-RECORDS.md) and the
[accounts/API/configuration handoff](ADMIN-ACCOUNTS.md). Tasks remain unchecked pending
review and linked PR evidence. Route geometry expansion still requires Member 2 review.

**Name:** unassigned  |  **Branch:** `feature/admin-interface`  |  **Interface:** `/admin`

### Frontend section

Build the trip history, event logs, search/filter and detail views. Add user, stop and route management screens as their validated backend functions become available.

**Frontend tools:** HTML, CSS, JavaScript, Fetch API, shared tables/forms and design tokens.

**Frontend files:** frontend/public/admin.html and admin.js (implemented; see FRONTEND-REVIEW.md).

- [x] **P3-01 Build trip and event views** - Show stored trips and events, detail rows and filters. Start from existing recent-record endpoints.
  - Done when: View shows real stored statuses; no invented counts or hard-coded business metrics.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)

### Backend section

Build shared accounts, sessions and passenger/operator/admin permissions. Enforce trip ownership; maintain database migrations, records, reporting, backup/restore and validated configuration updates. Supply the access contract to Members 1 and 2.

**Backend tools:** Python, FastAPI, SQLite/SQL, Pydantic, pytest, Ruff and a reviewed password/session library selected before account implementation.

**Backend / firmware files:** backend/taxi/storage.py (existing); backend/taxi/routers/admin.py, backend/taxi/auth.py and migration/access-control tests (planned).

Backend integration, verification and handoff checklist:

- [x] **P3-02 Design accounts and roles** - Define passenger, operator and admin permissions; implement secure identity/session handling and authorization.
  - Done when: Unauthenticated and wrong-role requests fail; passenger credentials never grant operator power.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)
- [x] **P3-03 Enforce trip ownership** - Add owner identity to trips using a documented schema migration and validate it on read/cancel.
  - Done when: Cross-passenger read/cancel tests fail safely; existing trip history remains usable.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)
- [x] **P3-04 Add configuration management** - Expose validated stop/route management after agreeing safe update rules with Member 2.
  - Done when: Invalid/unreachable routes are rejected; active missions cannot be silently changed underneath the supervisor.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)
- [x] **P3-05 Add reporting and storage discipline** - Calculate summaries from records; define pagination, migrations, backups and restore checks.
  - Done when: Reports match stored data and migration/restore tests are recorded.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)
- [x] **P3-06 Review and hand off** - Submit admin/auth work in small pull requests and provide the integration contract to Members 1 and 2.
  - Done when: Passenger and operator integrations pass role/ownership tests.
  - PR/evidence: [account/configuration contract](ADMIN-ACCOUNTS.md), [operations drill](PROBIX-OPERATIONS.md), [merge review](MERGE-REVIEW.md)

**Dependency:** Coordinate schema changes with Member 2 and passenger identity with Member 1. Payment/fleet features are later scope.

### Layman explanation section

You build the office and record book for the taxi service. The screen helps staff find past trips and manage approved information. The code behind it remembers who each person is, what they are allowed to do and which trip belongs to them. Example: a passenger can see their own ride, but cannot open another passenger's trip or use an operator's controls. Administrators can review records through authorized screens.

## Member 4 - Vehicle diagnostics, firmware and communication

**Name:** unassigned  |  **Branch:** `feature/diagnostics-interface`  |  **Interface:** `/diagnostics`

### Frontend section

Build the camera, sensor, board connection and fault panels. Show data source, measurement age and validity; distinguish simulation from real devices and missing data.

**Frontend tools:** HTML, CSS, JavaScript, camera/status panels, Fetch API, browser WebSocket and shared design tokens.

**Frontend files:** frontend/public/diagnostics.html and diagnostics.js (implemented for honest simulation/missing-device visibility).

- [x] **P4-01 Build diagnostics with honest source labels** - Display simulation/device source, sensor age, validity, camera state, connection and stop reasons; missing hardware is unavailable.
  - Done when: No absent sensor is shown as a fabricated healthy value.
  - PR/evidence: [frontend diagnostic checks](FRONTEND-REVIEW.md), [merge review](MERGE-REVIEW.md)

### Backend section - device firmware and hardware integration

Confirm hardware and wiring, compile and bench-test boards, read actual sensors and implement the read-only telemetry adapter. Later implement the tested motor interface, local watchdog and command freshness with Member 2. Board firmware is part of this workstream, separate from the laptop web backend.

**Backend tools:** Python telemetry parser/adapter, Arduino C/C++, PlatformIO or Arduino IDE, esp_camera, local HTTP, UART and optional PySerial for direct USB bench tests.

**Backend / firmware files:** firmware/esp32_cam/, firmware/arduino/ and scripts/camera_probe.py (existing starters); backend/taxi/communication/ and parser/timeout tests (planned).

Backend integration, verification and handoff checklist:

- [ ] **P4-02 Confirm actual hardware** - Record camera/Arduino models, driver, steering, power/logic levels, UART pins, sensor/feedback parts and independent stop wiring.
  - Done when: Hardware team confirms the wiring record before board-specific output code.
  - PR/evidence: _add link_
- [ ] **P4-03 Compile and test disarmed boards** - Build both targets; capture one JPEG; bench-test PING/STOP and telemetry relay with motors disabled.
  - Done when: Compiler logs and hardware observations recorded; STOP receipt is not called measured braking.
  - PR/evidence: _add link_
- [ ] **P4-04 Implement real sensors and read-only adapter** - Read actual ultrasonic/IMU/feedback data with timestamps/validity; add bounded parser and timeout handling.
  - Done when: Malformed, missing and stale samples are rejected; diagnostics displays measured values.
  - PR/evidence: _add link_
- [ ] **P4-05 Design and prove local motion protection** - After hardware confirmation, implement driver, command authority/watchdog, replay/expiry validation and fault/rearm handshake with Member 2.
  - Done when: Test old sessions, delayed/duplicate frames, link loss, resets and hardware disable before autonomy.
  - PR/evidence: _add link_
- [ ] **P4-06 Integrate measured feedback** - Provide tested telemetry/camera interfaces to Member 2 and run controlled-course checks only after the local stop gate passes.
  - Done when: Stopping behavior and timing are measured; failures lead to the defined stopped state.
  - PR/evidence: _add link_

**Dependency:** Blocked on exact hardware facts and successful board builds. Never enable physical outputs from guessed pins or simulated thresholds.

### Layman explanation section

You build the vehicle's health screen and the connections to its electronics. Think of your screen as the dashboard used by a mechanic: it shows what the camera and sensors are reporting and whether the boards are connected. Your firmware and communication code bring those readings to the laptop. Later, after testing the actual hardware, you connect movement commands to the motor controls. Example: a disconnected sensor must show unavailable rather than a made-up safe distance.

## First working session - do this in order

1. Assign the four real names and confirm the integration lead (Member 2 suggested).
2. All clone the repo and run the simulation/tests. Do not enable motors.
3. Agree API/state/role contracts and shared design tokens.
4. Member 1 builds passenger UI; Member 2 splits operator UI; Member 3 builds records UI and auth design; Member 4 builds diagnostics UI and confirms hardware.
5. Merge small reviewed PRs and demonstrate the connected simulation before connecting physical motion.

## Pull request and completion rules

- Preserve the working simulator; use a separate feature branch for each workstream.
- Avoid simultaneous edits to shared api.py/storage.py/styles; coordinate module boundaries first.
- Run pytest and Ruff, run JS syntax checks, and record browser checks for changed screens.
- Hardware claims require compiler and bench logs; simulation alone is not physical validation.
- Complete each task by editing `[ ]` to `[x]` in a reviewed PR and linking evidence. Readers without write access can suggest changes through PRs; this page does not grant repository access.
- Do not commit .env, Wi-Fi/device credentials, recordings or model weights.

## How Codex helps this plan

Codex can implement a selected task, prepare API/data contracts, create tests, investigate errors, review diffs and prepare PRs. Each member should start with: “Read AGENTS.md and docs/TEAM-WORKSPACE.md. Implement task Pn-xx in my workstream and run its checks.” Humans confirm hardware and wiring, perform physical tests and review measured results. No additional fifth team member is assumed.

## Useful references

- [Project setup](../README.md)
- [Architecture](ARCHITECTURE.md)
- [Existing engineering roadmap](ROADMAP.md)
- [Hardware checklist](HARDWARE.md)
- [Protocol contract](PROTOCOL.md)
- [Validation record](VALIDATION.md)
- [Successful initial CI](https://github.com/praisecyber/Autonomous-Taxi/actions/runs/39956785064)

Baseline code: b029b9d. Updated technical completion evidence: [29 October merge review](MERGE-REVIEW.md). Hardware and human handoffs remain pending as marked.
