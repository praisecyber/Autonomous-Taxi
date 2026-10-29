# Frontend/backend branch merge review — 29 October 2026

Reviewed incoming branch `feature/frontend-backend-split` at
[`629f048`](https://github.com/praisecyber/Autonomous-Taxi/commit/629f048)
against main
[`eeef5ff`](https://github.com/praisecyber/Autonomous-Taxi/commit/eeef5ff).
Main already contained the earlier frontend changes through PRs
[#1](https://github.com/praisecyber/Autonomous-Taxi/pull/1) and
[#2](https://github.com/praisecyber/Autonomous-Taxi/pull/2). The remaining two
commits place AI resources in the backend and add accounts/HTTPS operations.
The merge is conflict-free and retains both histories.

## Reviewed scope and conclusions

Reviewed application lifespan/one-database ownership, production host/scheme
checks, cookie/CSRF/session rules, password provisioning and required rotation,
role gates and telemetry redaction, schema migration, deployment proxy settings,
and the corresponding regression tests. No blocking integration defect was found
in this scope. This is a technical review; no individual teammate sign-off or
independent security audit is claimed.

- [Account/ownership/configuration contract](ADMIN-ACCOUNTS.md): admin and operator
  authority stay separate; passengers cannot select an owner or access foreign
  trips. Diagnostics is read-only. Configuration preserves version/state/map gates.
- [Regression tests](../backend/tests/test_deployment.py): schema-1 migration retains
  owner/session/configuration data; diagnostics restrictions, forced rotation,
  production fail-closed settings, secure cookies and database lease are covered.
- [Earlier integration review](INTEGRATION-REVIEW.md): one supervisor, shared routes,
  mission/fault rules and Member 1/2/3 contracts.
- [Frontend evidence](FRONTEND-REVIEW.md) and [browser runner](../scripts/check_admin_browser.py):
  shared black/green/yellow interface, role flows, responsive layouts, stale and
  disconnected states, keyboard focus and automated accessibility checks.
- [Operational restore evidence](PROBIX-OPERATIONS.md) and
  [reproducible drill](../scripts/https_restore_drill.py): verified local HTTPS/WSS,
  five copied account rotations, history/configuration retention, five revoked
  sessions on second restore and unchanged live source.
- [Deployment guide](../deploy/README.md): local CA trust and protected credentials;
  public DNS/server/certificate setup remains required before public sharing.

## Validation of the merged tree

Python 3.12: **43 tests passed**; Ruff passed; Node proxy test and operator JS syntax
passed, along with syntax checks for all first-party browser scripts. Chromium
passed the desktop/phone integration flows with no JavaScript errors, including
role/ownership, configuration, arrival, Stop, stale/invalid/disconnected telemetry,
fault retention, keyboard focus and Swagger session/CSRF flows. Axe detected zero
WCAG 2.1 A/AA violations in the tested views. Screenshots are local artifacts at
`/tmp/taxi-merge-review`; reproduce with the linked browser runner. The tests use isolated data and do not mutate the
provisioned live database. One upstream Starlette/httpx deprecation warning remains.
Current remote GitHub CI status is not asserted by these local results.

## Priority and limits

**Member 4 P4-02 is the first blocker for real vehicle integration.** Exact hardware,
wiring, power/logic levels, feedback and independent stop must be confirmed in the
[hardware handoff](HARDWARE.md#priority-1-confirmation-handoff), reviewed by Member 2,
then followed by disarmed builds and bench evidence. Firmware compilation, real
sensor operation, measured stopping and physical autonomy have not been verified.
The merge enables simulation and administrative workflows, not real vehicle motion.
The [team checklist](TEAM-WORKSPACE.md) separates completed technical evidence from
pending human handoffs and hardware gates.
