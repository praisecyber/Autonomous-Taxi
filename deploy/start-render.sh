#!/usr/bin/env bash
set -euo pipefail
umask 077
export TAXI_FRONTEND_ROOT="$PWD/frontend/public"
: "${RENDER_EXTERNAL_HOSTNAME:?Render hostname is required}"
: "${TAXI_DATA_DIR:?Persistent data directory is required}"
mkdir -p "$TAXI_DATA_DIR"
if [[ ! -f "$TAXI_DATA_DIR/taxi.sqlite3" ]]; then
  if [[ "${TAXI_BOOTSTRAP_NEW_DATABASE:-0}" != 1 ]]; then
    echo 'Restore the existing database or explicitly enable a fresh database bootstrap.' >&2
    exit 1
  fi
  python -m taxi.manage provision-accounts --database "$TAXI_DATA_DIR/taxi.sqlite3" \
    --manifest deploy/probix-accounts.json \
    --credentials-out "$TAXI_DATA_DIR/provisioning/initial-credentials.json"
fi
# Only use this entry point behind Render's managed ingress. The public listener
# receives platform TLS termination; local/Compose deployments use narrower trust.
exec python -m uvicorn taxi.render_service:create_render_app --factory \
  --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 \
  --proxy-headers --forwarded-allow-ips '*'
