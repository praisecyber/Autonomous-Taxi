# PROBIX operational readiness — 29 October 2026

Five local accounts were provisioned from `deploy/probix-accounts.json`, with
random temporary passwords, private credential delivery and mandatory first-login
rotation. The role assignment and local HTTPS instructions are in
[deployment guide](../deploy/README.md). No passwords are stored in Git.

## Completed integration review

Passenger ownership is derived from the authenticated identity; foreign trips are
hidden. Only operators issue vehicle commands; administrators manage records,
accounts and authorized configuration. Diagnostics cannot read private trips,
events or configuration, and cannot command the vehicle. Telemetry redacts private
trips for public/diagnostics clients. Configuration requires READY at A with no
trip/mission, validates the fixed connected map, and rejects stale versions.
Roles, ownership and existing configuration survive schema-2 migration.

## Operational drill evidence

Report: `runtime/operations/probix-restore-drill-20261029-r3/report.json` (private,
ignored runtime output). Source had five accounts, one completed trip and no sessions.
Backup SHA-256:
`5b37a382d7540ac243bdc9de3923ae0b04c8058c44a12674b1922ec272716456`.

The restored copy passed SQLite integrity/foreign-key checks and retained accounts,
trip history, ownership and configuration. Tests used real Caddy HTTPS, trusted
local CA verification and WSS, not a certificate-verification bypass. All five
copied accounts signed in and rotated passwords. Old sessions were revoked.
Passenger/operator/admin/diagnostics restrictions, active configuration rejection,
stale-version rejection, cancellation and reset were exercised. A second restore
revoked five stored sessions; fresh login succeeded. The live source stayed
byte-for-byte unchanged during this drill.

Backend regression suite: 43 passing tests. Browser regression and 18 axe WCAG
2.1 A/AA scans passed; this does not replace human accessibility review. Backend
and Caddy container images were built, Compose configuration validated, and the
live local HTTPS health endpoint verified with its CA certificate.

## Before public sharing

Supply a domain and deployment machine under your control, configure DNS/firewall,
transfer existing data using the documented restore procedure, obtain public TLS,
and verify the final origin. Deliver credentials privately and have users rotate
them. Schedule protected off-machine backups and repeat recovery drills. No public
service or certificate has been created. Hardware actuation remains unimplemented.
