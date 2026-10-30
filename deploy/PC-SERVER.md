# Project PC server

The PC hosts the Python backend, frontend files, Caddy HTTPS proxy and SQLite data.
Render is not used. This is a software simulation service. Keep exactly one backend
worker/supervisor per database. All browser traffic uses the same HTTPS origin.

## Linux or Windows with WSL2

The existing launcher is Bash-based. Use Linux, or Ubuntu in WSL2 on Windows with
Python 3.12. Run these commands inside that environment from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Install a verified Linux Caddy executable as `runtime/tools/caddy` and make it
executable. Use the official Caddy distribution, or the digest-pinned official image
listed in `Dockerfile.caddy`. The executable must match the operating system and
CPU; a Windows executable will not run inside Linux/WSL.

If this is a different PC from the existing installation, privately transfer a CLI
backup and restore it into a new runtime directory using the recovery runbook.
Do not commit/copy the database through Git or silently create replacement accounts.
If no accounts/database exist and a genuinely new installation is intended:

```bash
.venv/bin/python -m taxi.manage provision-accounts --database runtime/taxi.sqlite3 --manifest deploy/probix-accounts.json --credentials-out runtime/provisioning/initial-credentials.json
```

This generates new passwords and is not a migration of existing accounts. It refuses
to overwrite existing usernames or credentials. Protect the output and deliver each
entry privately. For existing accounts preserve their database and passwords.

Start the PC server:

```bash
deploy/start-local-https.sh
```

Keep the terminal running. The launcher starts one backend at 127.0.0.1:8000 and
Caddy at HTTPS 8443; HTTP 8080 redirects to HTTPS. Do not also start Node or a second
Python server. Native Windows service/automatic-start setup is not configured;
WSL must remain running. Disable sleep during a supervised serving session.

## Use on the server PC

Open `https://probix.localhost:8443/account`. Trust the public local CA certificate
`runtime/tls-local/data/caddy/pki/authorities/local/root.crt` in the browser/OS first.
For a Windows browser with the service in WSL, confirm Windows-to-WSL localhost
forwarding works and import only that public certificate into the intended trust
store. Do not import/distribute private CA keys or bypass certificate checks.

Sign in and change temporary passwords. Check `/api/health`, then run the passenger,
operator, diagnostics and admin walkthrough. The existing profile intentionally
binds loopback; it does not expose the PC to the LAN or Internet.

## If team members use other devices

`probix.localhost` on their phone/laptop points to their own device. LAN sharing
requires a stable server-PC address or local DNS name, firewall rules, a proxy
listener bound to the intended interface and a matching HTTPS certificate trusted
by clients. WSL may additionally require networking/forwarding configuration.
Do not simply expose port 8000 or set wildcard allowed hosts. Keep Python on loopback;
only the HTTPS proxy should accept client traffic.

The exact PC OS and desired access scope (same PC or LAN) have not been supplied.
LAN binding and firewall changes are therefore not applied. No router forwarding,
public domain, or Internet access is needed for same-PC use.

## Data, backups and recovery

Keep `runtime/taxi.sqlite3` and credentials private on the server PC. Run:

```bash
.venv/bin/python scripts/backup_checkpoint.py
```

Check its receipt and periodically exercise restore on an isolated copy. A backup
on the same disk is insufficient for disk loss; select an encrypted external drive
or a protected separate destination. No destination, automatic timer or pruning
has been configured. Follow [Member 3 recovery/retention runbook](../docs/MEMBER3-SOFTWARE-HANDOFF.md).

Stop with Ctrl+C in the launcher terminal. Preserve data before upgrades and never
run two backends against it. After restarting, verify HTTPS health, fresh login,
WSS telemetry and role boundaries before handing the service to the team.
