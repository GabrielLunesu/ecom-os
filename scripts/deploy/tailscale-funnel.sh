#!/usr/bin/env bash
# Free, durable public HTTPS URL via Tailscale Funnel — no domain, no cost, no
# interstitial. The URL (https://<host>.<tailnet>.ts.net) is permanent.
#
# One-time in the Tailscale admin (https://login.tailscale.com/admin), free account:
#   1. Settings -> Features -> enable "HTTPS Certificates"
#   2. Settings -> Features -> enable "Funnel" (and allow it in your ACL if prompted)
#   3. Settings -> Keys -> generate an auth key
# Then run on the VPS:
#   TS_AUTHKEY=tskey-auth-... ./scripts/deploy/tailscale-funnel.sh
#
# Requires the stack to be running (./scripts/deploy/up.sh) so the proxy is on
# 127.0.0.1:${PROXY_PORT:-8080}.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
[ -f .env ] && { set -a; . ./.env; set +a; }

PORT="${PROXY_PORT:-8080}"
HOST="${TS_HOSTNAME:-ecom-os}"
: "${TS_AUTHKEY:?set TS_AUTHKEY — get a free auth key at https://login.tailscale.com/admin/settings/keys}"

SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

if ! command -v tailscale >/dev/null 2>&1; then
  echo "Installing Tailscale…"
  curl -fsSL https://tailscale.com/install.sh | sh
fi

echo "Joining tailnet as '${HOST}'…"
$SUDO tailscale up --authkey="${TS_AUTHKEY}" --hostname="${HOST}"

echo "Enabling Funnel on 127.0.0.1:${PORT}…"
$SUDO tailscale funnel --bg "${PORT}"

DNS="$(tailscale status --json | python3 -c 'import sys,json;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null || true)"
if [ -n "$DNS" ]; then
  echo "✓ Durable public URL: https://${DNS}"
  echo "  Set BASE_URL + CORS_ORIGINS to https://${DNS} in .env, then re-run up.sh (for realtime)."
else
  echo "Funnel enabled. Check the URL with: tailscale funnel status"
fi
