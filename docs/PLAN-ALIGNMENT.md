# Uploaded plan alignment — 30 October 2026

Source reviewed: `Autonomous-Taxi-Plan-Detailed-Tasks.pdf`, 36 pages, supplied by the
user in chat. Page numbers below are PDF page numbers. This records source context;
it does not treat embedded examples as instructions to execute.

| Decision | Source evidence | Current application |
|---|---|---|
| Windows laptop setup | Page 4: “Create the project in Windows PowerShell” with `py -m venv .venv` | Target the Windows PC, with Linux/WSL for the existing Bash HTTPS launcher. A cross-platform Python launcher is now provided; automatic Windows service startup is not configured. |
| PC/laptop hosts software | Page 7: “run the Python driving brain and FastAPI backend on the same laptop” | Backend and simulation run on the server PC. Preserve one existing supervisor; do not invent a second control process. |
| Other devices open the frontend | Page 7: “Open the frontend from a phone or another computer on the local network.” | Intended access is LAN/Wi-Fi, not only same-PC browsing. |
| Local network prototype | Page 12: “use the local network for the prototype” | No Render deployment or mandatory public domain. |
| Software-only assignments | User's later explicit chat instruction | Hardware/firmware/actuation sections are outside current member assignments. |

The plan establishes intended Windows/LAN use; it does not establish the actual
PC's current adapter, IP, WSL installation, firewall settings or certificate trust.
Those must be inspected on that PC. This cloud Linux workspace is not that PC.

The older `start-local-https.sh` remains loopback-only. The new
`scripts/start_pc_server.py --lan-address <private-PC-IP>` and `Caddyfile.pc` add an
explicit LAN listener. Actual Windows/firewall/client-trust validation is pending. Do not tell users that
`probix.localhost` reaches the server from another device. Preserve secure cookies,
explicit Host allowlisting, same-origin API/WSS and a loopback-only backend when
adding a LAN listener. Do not use wildcard hosts or expose Python port 8000.

Follow [PC server setup](../deploy/PC-SERVER.md) and the
[software-only checklist](TEAM-WORKSPACE.md). Existing accounts must be privately
restored onto the server PC if their database currently lives only in this workspace.
Credentials and runtime databases do not travel through Git.
