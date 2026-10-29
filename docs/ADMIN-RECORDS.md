# Member 3 implementation and validation

Work is on `feature/admin-interface`. P3-01 through P3-05 have local implementation and
validation; P3-06 has an integration contract and runnable integration checks. Human review,
Member 2 agreement on configuration limits, a PR and merge remain outstanding. Checklist
boxes stay unchecked until reviewed evidence is linked.

## Implemented

- `/admin`: account-based administrator login, paginated/searchable trip/event views,
  expandable text-safe details, real stored-record summaries, user creation/access
  revocation, and versioned simulation configuration.
- `/account`: shared identity/session handling, password changes and a passenger-owned
  booking/cancellation integration view. Operator sessions work in the original dashboard.
- Role enforcement, cookie/CSRF protection, trip ownership, old-history migration and
  offline backup/restore with integrity checks and session revocation.
- [Integration contract and operating instructions](ADMIN-ACCOUNTS.md).

## Validation — 29 October 2026

- Python 3.12: 30 pytest tests, covering the original simulator plus authentication,
  wrong-role denial, cross-passenger read/cancel, session expiry/logout/revocation,
  password change, migration preservation, configuration gates/versions, pagination,
  reports and backup/restore. One upstream Starlette/httpx deprecation warning.
- Ruff, JavaScript syntax checks for operator/admin/account, and dependency consistency.
- Real Chromium against a temporary database: login failures and admin access, actual
  stored reports, server-side pagination/search, text-safe details, account creation and
  revocation, passenger-owned booking/cancellation, operator session controls, configuration
  rejection during a trip and save after reset, sign-out, and unavailable-network feedback.
- Desktop (1440 px) and phone (390 px) layouts checked. Tables scroll inside panels;
  the document does not overflow. No browser JavaScript exceptions.
- Browser tests create only disposable synthetic accounts; the temporary server/database
  are removed afterward. No real admin password is created by the implementation.
- No physical hardware, firmware or production deployment validation was performed.

Reproduce:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
node --check taxi/static/app.js
node --check taxi/static/admin.js
node --check taxi/static/account.js
.venv/bin/python -m pip check
```

Optional browser checks:

```bash
.venv/bin/python -m pip install -e '.[dev,browser]'
.venv/bin/python scripts/check_admin_browser.py --chromium /usr/bin/chromium
```

Without system Chromium, install the Playwright Chromium runtime and omit `--chromium`.
Use `--screenshots /tmp/taxi-review` to save review captures outside Git.
