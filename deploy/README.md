# PROBIX HTTPS deployment

The running local service uses `https://probix.localhost:8443/account`. This is a
loopback hostname, not an Internet domain or a public deployment. The app remains
a simulation: no physical vehicle motion is implemented.

## Accounts and first login

The provisioned local database is `runtime/taxi.sqlite3`:

| Username | Role |
|---|---|
| probix | admin |
| probix.member1 | passenger |
| probix.member2 | operator |
| probix.member3 | admin |
| probix.member4 | diagnostics |

Initial passwords are in the owner-only, ignored file
`runtime/provisioning/probix-initial-credentials.json`. Deliver each person's entry
privately; never commit, paste into chat, or distribute the complete file to the
team. Every account must change its password at `/account` before workspace access.
Changing passwords revokes all sessions and requires signing in again. Admins do
not inherit operator controls. Diagnostics is read-only and cannot read private
trip history or issue commands. Confirm this proposed member-to-role assignment
with the team before distributing credentials.

## Local HTTPS

From the repository root, stop any existing backend before running:

```bash
deploy/start-local-https.sh
```

This starts one Python backend on loopback port 8000 and Caddy on HTTPS 8443,
with HTTP 8080 redirecting to HTTPS. Caddy serves the frontend and proxies API/WSS
on the same origin. No Node server is needed for this profile. The launcher expects
`.venv` dependencies and `runtime/tools/caddy`. The tested Caddy is 2.10.2, extracted
from the digest-pinned official image in `Dockerfile.caddy`; install a verified
Caddy binary there when preparing a fresh machine.

Trust only the public local CA certificate
`runtime/tls-local/data/caddy/pki/authorities/local/root.crt` in your browser/OS
before browsing. Never distribute the adjacent private CA keys. Do not bypass
certificate verification. The hostname resolves to the machine where the browser
runs: accessing this cloud workspace from another machine needs an explicitly
configured secure tunnel or a proper public deployment.

Production mode refuses insecure cookie settings, legacy shared-token access,
missing explicit allowed hosts, and startup without an enabled administrator.
It rejects plain HTTP except health checks. Only the configured proxy IP may
supply forwarded scheme information. The database lease prevents two backend
processes or offline provisioning from owning one database concurrently.

## Public host preparation

No public hostname has been registered and no public certificate has been issued.
Choose a domain you control, point DNS to your deployment machine, and open inbound
TCP 80/443 (UDP 443 is optional HTTP/3). Install Docker/Compose. Copy
`deploy/production.env.example` to ignored `runtime/production.env`, replace the
placeholder domain, and ensure the private subnet does not overlap host networks.
Change the subnet and both static IPs together if needed.

```bash
docker compose --env-file runtime/production.env -f deploy/compose.yaml config --quiet
docker compose --env-file runtime/production.env -f deploy/compose.yaml build
```

For a genuinely new installation only, provision the initially empty volume before
starting the backend:

```bash
docker compose --env-file runtime/production.env -f deploy/compose.yaml run --rm --no-deps backend python -m taxi.manage provision-accounts --database /data/taxi.sqlite3 --manifest /app/deploy/probix-accounts.json --credentials-out /data/provisioning/initial-credentials.json
docker compose --env-file runtime/production.env -f deploy/compose.yaml up -d
```

Retrieve credentials privately from the backend's protected data volume. This
creates new accounts/passwords, not the existing local database. To deploy existing
data, stop its backend, create a CLI backup, transfer that backup privately and
restore it into a new path in the deployment data volume using `taxi.manage restore`.
Select the restored database deliberately and give UID/GID 10001 ownership. Never
replace the existing volume silently or run two backends against the same database.
Restore revokes sessions and interrupts active trips. Retain the original and an
off-machine encrypted backup. Do not use `docker compose down --volumes` on live data.

Caddy obtains public TLS certificates only after valid DNS/reachability. Only Caddy
publishes ports; the backend remains on the internal network. Backend runs as UID
10001 with one worker, read-only root filesystem and restricted capabilities.
Health checks alone do not prove HTTPS: verify login, forced password changes,
role boundaries and WSS from the final public origin before sharing.

## Backup/restore drill

Stop the source backend, then run against a new output directory:

```bash
.venv/bin/python scripts/https_restore_drill.py --source runtime/taxi.sqlite3 --credentials runtime/provisioning/probix-initial-credentials.json --output runtime/operations/new-drill
```

The initial-password drill is intended before credential distribution. After users
rotate passwords, use separately authorized test accounts and an appropriate
private credentials file. The drill never changes source credentials: all login,
password rotation, trip/configuration mutations and second restore happen on copies.
Keep backup files and drill logs private. See `docs/PROBIX-OPERATIONS.md` for the
completed drill evidence and `docs/ADMIN-ACCOUNTS.md` for permission/configuration rules.

## Selected managed hosting: Render

See [Render setup](RENDER.md) and the root `render.yaml` Blueprint for same-origin
frontend/API hosting with persistent SQLite. Account creation in Render and encrypted
off-machine backups remain pending; local credentials are not automatically migrated.
