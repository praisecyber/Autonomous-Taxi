# Project PC server

The PC hosts the Python backend, frontend files, Caddy HTTPS proxy and SQLite data.
Render is not used. This is a software simulation service. The cross-platform
launcher below now supports explicit LAN binding. Keep exactly one backend
worker/supervisor per database. All browser traffic uses the same HTTPS origin.

## Planned operating system and access

The uploaded detailed plan specifies Windows PowerShell (PDF page 4), with phones
or other computers accessing the laptop frontend over the local network (page 7).
Use **Windows PC + local-network clients** as the intended deployment. See
[plan alignment](../docs/PLAN-ALIGNMENT.md). The new Python launcher runs on Windows or Linux; automatic Windows service
installation is not configured. The Bash launcher remains the loopback/WSL option.

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
The Python launcher can bind an explicitly supplied private PC address. Firewall
and client trust changes are not applied to the user's PC from this cloud workspace. No router forwarding,
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
the selected Python environment; use the cross-platform Python launcher below for native Windows.

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

## Native Windows / LAN launch

Install Python 3.12 and a verified Windows Caddy executable. Keep the checkout and
runtime data in a private user directory. From PowerShell at the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
# Put the verified Windows binary at runtime\tools\caddy.exe.
```

Restore/provision the database using the earlier instructions first. Stop any older
server before starting this one. Choose the IPv4 address of this PC's intended LAN
adapter from the inspection command above. Example only, replace this address:

```powershell
.\.venv\Scripts\python.exe scripts\start_pc_server.py --lan-address 192.168.1.20 --check
.\.venv\Scripts\python.exe scripts\start_pc_server.py --lan-address 192.168.1.20
```

`--check` validates configuration/executable/ports without starting servers; it does
not establish successful database startup or client access. Omit `--lan-address`
for loopback-only `probix.localhost`. The LAN address must be an RFC1918 private IPv4
address actually bindable on this PC. Ports are configurable and must be different.
Do not run the Bash launcher at the same time.

For the example LAN address, clients open `https://192.168.1.20:8443/account`.
Only the selected IP is an allowed host. The backend remains at 127.0.0.1:8000.
After startup, the new public CA certificate is:
`runtime/tls-pc/data/caddy/pki/authorities/local/root.crt`.
This is a different CA location from the older Bash launcher. Transfer and trust
only this public certificate on the intended Windows/phone clients; never transfer
private keys. Validate the certificate identity through a trusted channel.
Keep runtime files/logs restricted using Windows filesystem permissions; POSIX 0600
modes alone do not configure Windows ACLs.

On a trusted Windows Private network, an administrator can add a limited rule
(replace the IP; do not run on an untrusted/public network):

```powershell
New-NetFirewallRule -DisplayName 'PROBIX HTTPS LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8443 -LocalAddress 192.168.1.20 -RemoteAddress LocalSubnet -Profile Private
```

HTTPS port 8443 is sufficient; HTTP 8080 redirect is optional. Do not open backend
port 8000 or add router forwarding. Native Windows avoids WSL forwarding requirements.
Client isolation on guest Wi-Fi can still prevent access. Prefer a DHCP reservation
for the PC; an address change requires restart, updated client URLs and matching
certificate trust checks. No firewall rule is applied automatically.

Keep the launcher terminal open. Ctrl+C stops both children; any child exit stops
the other. Private logs are under `runtime/tls-pc/`. Check HTTPS readiness using:

```powershell
.\.venv\Scripts\python.exe scripts\check_pc_server.py --origin https://192.168.1.20:8443 --ca runtime\tls-pc\data\caddy\pki\authorities\local\root.crt
```

The launcher/configuration were tested in this Linux workspace against an isolated
restored database, including verified local HTTPS and shutdown. Native Windows
execution, Windows firewall and phone trust have not been tested here; verify them
on the server PC before declaring LAN rollout complete. Automatic start at boot,
off-machine backup scheduling and user credential delivery remain separate steps.

## Optional current-user Windows tasks

After manual Windows startup, LAN HTTPS and a backup run have passed, use the task
helper on that PC. Review the PowerShell file before running; if local execution
policy blocks it, follow your administrator's signed-script policy. No task has
been registered from this cloud environment.

Prepare a private backup folder in `runtime\backups\checkpoints`. In Windows
Security → Advanced, restrict allow permissions to the service user, SYSTEM and
Administrators. Review inherited entries; do not alter unrelated project directories.
The backup command checks Windows ACLs instead of relying on misleading POSIX mode
bits. It refuses broader allow entries and never silently rewrites ACLs.

Examples, replacing the LAN address and selecting a suitable **local PC time**:

```powershell
# Preview only:
.\scripts\register_pc_task.ps1 -Kind Server -LanAddress 192.168.1.20 -WhatIf
.\scripts\register_pc_task.ps1 -Kind Backup -BackupAt '19:00' -WhatIf
# Register only after reviewing and testing the configuration:
.\scripts\register_pc_task.ps1 -Kind Server -LanAddress 192.168.1.20
.\scripts\register_pc_task.ps1 -Kind Backup -BackupAt '19:00'
```

19:00 is an example, not an assigned team deadline or configured schedule. The server
task starts at that user's next sign-in; the backup task runs daily while the user
is signed in and catches missed runs when available. No password is stored; neither
task runs as administrator or starts immediately on registration. They do not run
before login, wake a sleeping PC or provide unattended boot service. Keep the PC
awake during serving. Existing tasks are never overwritten; duplicate launches are
ignored by task settings, and the database lease/port checks protect the application.

Review task execution:

```powershell
Get-ScheduledTaskInfo -TaskName PROBIX-Server
Get-ScheduledTaskInfo -TaskName PROBIX-Backup
```

For the server, a running task is expected during service. For backup, inspect
LastRunTime/LastTaskResult (0 indicates successful completion), new checkpoint and
hash receipt. Task registration alone proves neither the job nor recovery works.
Server logs remain under `runtime\tls-pc`. A local checkpoint remains local; it does
not establish encrypted external storage or a restore drill. Disk space/retention
must be monitored; no automatic deletion is enabled.

Stop the application through its foreground launcher for a graceful shutdown when
possible. Windows Task Scheduler can terminate a process tree abruptly; after a
forced stop, verify no old listener remains before restart. To remove prepared tasks:

```powershell
Unregister-ScheduledTask -TaskName PROBIX-Server -Confirm
Unregister-ScheduledTask -TaskName PROBIX-Backup -Confirm
```

Native Windows Task Scheduler and ACL behavior are not executable in this Linux
workspace. Test both on the actual Windows PC before relying on unattended operation.
