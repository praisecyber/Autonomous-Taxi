# Project PC server

The PC hosts the Python backend, frontend files, Caddy HTTPS proxy and SQLite data.
Render is not used. This is a software simulation service. Keep exactly one backend
worker/supervisor per database. All browser traffic uses the same HTTPS origin.

## Planned operating system and access

The uploaded detailed plan specifies Windows PowerShell (PDF page 4), with phones
or other computers accessing the laptop frontend over the local network (page 7).
Use **Windows PC + local-network clients** as the intended deployment. See
[plan alignment](../docs/PLAN-ALIGNMENT.md). The current Bash launcher runs in
Linux/WSL; it is not a native Windows service, and LAN sharing is not enabled yet.

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

The uploaded plan establishes Windows and LAN use. The actual Windows version,
WSL networking mode and active PC LAN address have not been inspected here.
LAN binding and firewall changes are not applied to the user's PC from this cloud
workspace. No router forwarding,
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

## Read-only readiness check

After startup, run this on the server PC:

```bash
.venv/bin/python scripts/check_pc_server.py --ca runtime/tls-local/data/caddy/pki/authorities/local/root.crt
```

Use `--origin https://<pc-host>:<port>` for an explicitly configured reachable origin.
The check verifies the certificate/hostname, health, pages, stylesheet and API docs
without signing in or changing records. It connects directly to the selected PC
and does not use an outbound proxy. It does not verify login, session permissions
or WSS; run the separate browser/operational checks for those. No insecure TLS mode
is provided. On Windows native Python, use `.venv\Scripts\python.exe` if that is
the selected Python environment; the server launcher currently uses Linux/WSL.

## Inspect the Windows server PC before LAN setup

Run in PowerShell on that PC, not in this cloud workspace:

```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress
wsl --status
```

Use the adapter for the intended trusted local network; do not choose a VPN/virtual
adapter blindly. Keep the backend on loopback. LAN rollout needs a chosen reachable
PC IP/name, a proxy listener for that interface, a certificate matching that IP/name,
client trust in its public CA and a narrowly scoped Windows firewall rule. WSL may
need forwarding or mirrored networking depending on its version. Do not apply
broad firewall or router changes from guessed network details. These inspection
commands do not enable network access or reveal application passwords.
