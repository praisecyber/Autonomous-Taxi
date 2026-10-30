# Render deployment

Render is the selected hosting target. This repository now includes `render.yaml`
and `deploy/start-render.sh`. No Render service has been created from this workspace;
no authenticated Render connector is available. An `onrender.com` hostname will be
assigned by Render; its exact value and availability are not assumed here.

## Create the service

1. Sign in to Render, connect `praisecyber/Autonomous-Taxi`, select **New → Blueprint**,
   and use branch `main` / root `render.yaml`.
2. Review the paid Starter service and 1 GB persistent disk charges before creating
   resources. Persistent SQLite storage is required; do not substitute an ephemeral
   free service. Keep one instance and one backend worker.
3. Choose the data path below **before first startup**. Default bootstrap is off,
   so a missing database fails explicitly instead of silently generating new accounts.
4. Deploy after the data decision is made. Render supplies the external hostname,
   PORT and managed TLS. The entry point restricts allowed hosts to the assigned name.

### New installation, explicitly selected

Set `TAXI_BOOTSTRAP_NEW_DATABASE=1` in Render before the first deploy. Startup creates
five new accounts using the nonsecret role manifest, with different random temporary
passwords from the local installation. This is not a migration of local data.
Initial credentials are stored only on the persistent disk at
`/var/data/taxi/provisioning/initial-credentials.json`; access them privately via
Render Shell, and distribute only each recipient's own entry. Do not paste the
file into tickets/logs/chat. Every account must rotate on first login.
After successful provisioning, set the bootstrap variable back to `0`.

### Existing local data

Preserve and migrate the existing protected backup rather than treating new accounts
as the same installation. Arrange an authenticated private file transfer and disk
access in Render first; neither is configured by this Blueprint. Restore with
`python -m taxi.manage restore --source <private-backup> --output <new-directory>/taxi.sqlite3`
on the persistent disk. Keep the original and explicitly select the restored directory
with `TAXI_DATA_DIR`. Stop the backend before switching databases. Never overwrite
an in-use database or commit/upload it as a public repository asset. Restore revokes
sessions and interrupts active simulated trips. This data-transfer step remains
pending; do not claim existing accounts/history have reached Render.

## Verify before sharing

Visit `https://<assigned-host>/account`, sign in and rotate temporary credentials.
Run the documented admin/passenger/operator/diagnostics walkthrough and verify WSS,
Secure/HttpOnly/SameSite cookies, role restrictions, stored reports and configuration
conflicts at that final origin. Check `/api/health` returns simulation mode. The local
Render adapter test verifies routing/Host/HTTPS/file isolation, not Render's actual
network or deployed TLS certificate.

This entry point trusts forwarded scheme headers from Render's ingress; deploy it
only as a Render managed web service. Do not expose this listener independently.
The local/Compose profiles retain their narrower proxy trust configuration.
Custom domains require updating the allowed-host configuration deliberately; the
initial adapter supports the Render-assigned hostname only.

## Backups

Persistent disk is not an independently verified off-machine backup. Run
`python scripts/backup_checkpoint.py --source /var/data/taxi/taxi.sqlite3 --directory /var/data/taxi/backups`
in Render Shell (adjust the source if selecting a restored directory). Follow the
[Member 3 recovery/retention runbook](../docs/MEMBER3-SOFTWARE-HANDOFF.md).
An encrypted backup destination and key owner still need selection; none has been
configured. Disk snapshots and plan features must be checked in your Render account.

References: [Render Blueprints](https://render.com/docs/blueprint-spec),
[persistent disks](https://render.com/docs/disks),
[web services](https://render.com/docs/web-services).
