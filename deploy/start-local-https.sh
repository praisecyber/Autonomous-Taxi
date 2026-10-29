#!/usr/bin/env bash
set -euo pipefail
umask 077
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
export TAXI_DOMAIN="${TAXI_DOMAIN:-probix.localhost}"
if [[ "$TAXI_DOMAIN" != *.localhost && "$TAXI_DOMAIN" != localhost ]]; then
  echo 'Use a .localhost name here; public HTTPS uses deploy/compose.yaml.' >&2
  exit 1
fi
export TAXI_DEPLOYMENT=production TAXI_MODE=simulation
export TAXI_SECURE_COOKIES=1 TAXI_ALLOW_LEGACY_TOKEN=0
export TAXI_ALLOWED_HOSTS="$TAXI_DOMAIN"
export TAXI_DATA_DIR="${TAXI_DATA_DIR:-$repo_dir/runtime}"
export TAXI_BACKEND_PORT="${TAXI_BACKEND_PORT:-8000}"
export TAXI_HTTPS_PORT="${TAXI_HTTPS_PORT:-8443}" TAXI_HTTP_PORT="${TAXI_HTTP_PORT:-8080}"
export TAXI_FRONTEND_ROOT="$repo_dir/frontend/public"
export TAXI_API_UPSTREAM="127.0.0.1:$TAXI_BACKEND_PORT"
export XDG_DATA_HOME="$repo_dir/runtime/tls-local/data"
export XDG_CONFIG_HOME="$repo_dir/runtime/tls-local/config"
mkdir -p runtime/tls-local
if [[ ! -x runtime/tools/caddy ]]; then
  echo 'Install the verified Caddy executable at runtime/tools/caddy first; see deploy/README.md.' >&2
  exit 1
fi
backend_pid='' caddy_pid=''
cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$caddy_pid" ]]; then kill "$caddy_pid" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
.venv/bin/python -m uvicorn taxi.api:create_app --factory --host 127.0.0.1 \
  --port "$TAXI_BACKEND_PORT" --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1 \
  >runtime/tls-local/backend.log 2>&1 &
backend_pid=$!
runtime/tools/caddy run --config deploy/Caddyfile.local --adapter caddyfile \
  >runtime/tls-local/caddy.log 2>&1 &
caddy_pid=$!
echo "Local HTTPS profile starting for $TAXI_DOMAIN on port $TAXI_HTTPS_PORT; one backend worker."
wait -n "$backend_pid" "$caddy_pid"
