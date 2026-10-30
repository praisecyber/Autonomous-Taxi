# Member 3 software handoff — 30 October 2026

Scope: accounts, admin/API demonstration, configuration validation, HTTPS configuration
and software recovery. No hardware tasks are included.

## Account and role checklist

Read-only inspection of the provisioned database confirmed the following enabled
accounts. This verifies configured roles, not individual team acceptance or delivery.

| Account | Configured role | First change still required |
|---|---|---|
| probix | admin (primary) | Yes |
| probix.member1 | passenger | Yes |
| probix.member2 | operator | Yes |
| probix.member3 | admin | Yes |
| probix.member4 | diagnostics | Yes |

- [x] Database integrity check returned `ok`; all five roles match the requested roster.
- [x] Credentials file is owner-only (0600), excluded from Git, and omitted from this report.
- [x] All five credentials authenticated and mandatory rotation worked **on restored copies**.
- [x] Old sessions were rejected after rotation on those copies.
- [ ] Each person receives only their own entry privately from the account owner.
- [ ] Team acknowledges assignments and each person changes their live password.

No credential was sent to another person. Do not mark delivery or live rotation
complete based on a test of a copy. Administrators cannot issue operator commands;
operators cannot manage accounts/configuration; diagnostics cannot read private
trips/events or command the simulator. All members use `/account` for password changes.

## Repeatable admin demonstration

Use isolated test data, not live account changes. From the repository root:

```bash
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium --screenshots /tmp/member3-admin-20261030 --axe /tmp/taxi-axe/axe.min.js
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

On 30 October, the browser runner passed with no JavaScript errors, and axe detected
zero WCAG 2.1 A/AA violations in the tested views. All 43 backend tests and Ruff
passed; one upstream Starlette/httpx deprecation warning remains.

The optional axe path must point to a verified local axe distribution. Omit `--axe`
if unavailable and do not claim accessibility scans ran. The browser runner creates
and removes its own test users/databases/processes. It covers login, admin records,
search/pagination/reports, account creation/revocation, text-safe details, configuration
save/gates, role separation and Swagger session/CSRF flows. It also exercises the
connected simulation and phone/desktop state handling.

Configuration evidence: [test_accounts.py](../backend/tests/test_accounts.py),
`test_configuration_gate_validation_version_and_restart`,
`test_unauthenticated_admin_denial_and_invalid_road_segments`, and
`test_configuration_cannot_clear_faults_or_change_an_active_route`.
Expected results: invalid graph/stop input 422, stale version 409, active/faulted
mission update 409, permitted READY-at-A change accepted and persisted.

## Recovery runbook

Keep original data and use a new output path for every operation. Example filenames
below were used for this run; choose new names for subsequent runs.

```bash
umask 077
.venv/bin/python -m taxi.manage backup --source runtime/taxi.sqlite3 --output runtime/backups/member3-20261030.sqlite3
.venv/bin/python scripts/https_restore_drill.py --source runtime/backups/member3-20261030.sqlite3 --credentials runtime/provisioning/probix-initial-credentials.json --output runtime/operations/member3-20261030
```

The SQLite backup API creates a consistent snapshot of the running database. The
drill takes a lease on that offline snapshot and makes further copies. Its unchanged
source assertion applies to the snapshot, not to a concurrently running live database.
No live passwords or trip/configuration records are changed by the drill.
The initial-credential drill requires accounts that still need first rotation; after
live rotation, use separately authorized test credentials and suitable isolated data.

For an actual recovery: stop the backend, retain its original database, use
`taxi.manage restore --source <protected-backup> --output <new-directory>/taxi.sqlite3`,
verify integrity/history/ownership/configuration on the copy, then explicitly select
that directory with `TAXI_DATA_DIR`. Start one backend only. Restore revokes sessions
and interrupts active trips; users must sign in again. Never overwrite the original
or restore over a running database. Record operator, backup hash, time and results.

Fresh drill report: `runtime/operations/member3-20261030/report.json` (private).
Five accounts and one completed trip were retained; five sessions were revoked on
second restore. Verified local HTTPS and WSS, forced rotation, permissions, admin
record lookup, configuration gates and fresh login passed. Backup SHA-256:
`b4916b262b793cec8265bb3138a915cba8bcd620471aa9d9dde393b634874599`.

## Backup retention, access and credentials

Operational policy for Member 3 to put into service:

- Take a backup daily and before migrations/deployment; retain 7 daily and 4 weekly
  recovery points. Keep the pre-change backup until post-change recovery is verified.
- Keep local backup directories owner-only and backup files 0600. Restrict access to
  designated admins; backups contain password hashes and personal records.
- Copy backups to an encrypted off-machine destination with separate restricted
  credentials. Keep decryption/recovery material separately accessible to the recovery
  owner. Verify the transferred hash and restore before relying on the destination.
- Run a recovery drill monthly and after schema changes. Review retention before
  deletion; retain at least one tested good copy. No automatic deletion is enabled.
- Deliver each initial credential privately; never put passwords in arguments, Git,
  tickets, logs, screenshots or this report. Review the initial credential file after
  all users rotate, then securely retire it under the service owner's retention policy.

Daily scheduling, off-machine storage and encryption key custody are **not configured**:
no destination or service owner was supplied. Member 3 is the role owner; a named
person, access list and destination still need assignment.

## HTTPS and deployment readiness

Reviewed [deployment configuration/runbook](../deploy/README.md): explicit allowed
hosts, secure HttpOnly/SameSite cookies, shared token disabled in production,
trusted proxy IP, internal backend, one worker and persistent protected data.
The local service was found stopped, restarted with `deploy/start-local-https.sh`,
and its `https://probix.localhost:8443/api/health` returned `ok: true` in simulation
mode. Local TLS verification used the public local CA certificate; no verification bypass.
Public Caddy configuration includes HTTPS and HSTS; test the actual public origin
before sharing. Local `probix.localhost:8443` is not an Internet deployment.

Remaining deployment inputs: controlled public domain/DNS, hosting target and access,
firewall/reachability, named service owner, protected off-machine backup destination
and recovery key custody. No public hostname/certificate/service is claimed.

## Prepared private delivery and backup checkpoints

Individual initial-credential files are prepared under ignored, owner-only
`runtime/provisioning/individual/`, named `<username>.json`. Each file contains only
that account's entry and is mode 0600. The master credential file was preserved.
These files are ready for the account owner to deliver privately; preparation does
not establish delivery, recipient acceptance or live rotation. Do not share the
whole directory or use initial credentials after that user has rotated.

Repeatable local backup command (from repository root):

```bash
.venv/bin/python scripts/backup_checkpoint.py
```

Defaults: source `runtime/taxi.sqlite3`, output `runtime/backups/checkpoints`.
Use `--source` and `--directory` for another database/location. Existing output
directories must be owner-only (0700); the command refuses broader permissions.
Each run creates a uniquely named private database and SHA-256 receipt without
replacing/deleting previous copies. A successful checkpoint is not proof of an
off-machine copy or a restore drill; its receipt explicitly marks both false.

The command was exercised on the actual local database. Isolated checks verified
unique outputs, matching receipt hashes, mode-0600 files, rejection of a nonprivate
directory and preservation of previous copies. Existing backup/restore regression
checks remain the recovery evidence. No timer, automatic pruning or remote transfer
has been enabled. Once the deployment owner/destination is selected, run this command
daily under that service account and monitor nonzero exits; use the documented
7-daily/4-weekly policy only after verifying at least one recoverable remote copy.
