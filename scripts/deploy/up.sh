#!/usr/bin/env bash
# Ecom-OS one-command production deploy (always-on VPS).
# Brings up the full single-origin stack via Docker Compose and waits for health.
#
#   ./scripts/deploy/up.sh
#
# Requires: Docker + Docker Compose v2, and a `.env` at the repo root (copy from
# .env.prod.example and fill in). If TUNNEL_TOKEN is set, the Cloudflare Tunnel
# is started too (a real HTTPS hostname, no inbound ports opened).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

err() { printf '\033[31m✖ %s\033[0m\n' "$*" >&2; }
ok() { printf '\033[32m✓ %s\033[0m\n' "$*"; }
info() { printf '• %s\n' "$*"; }

command -v docker >/dev/null || { err "docker not found — install Docker Engine + Compose v2"; exit 1; }
docker compose version >/dev/null 2>&1 || { err "docker compose v2 not found"; exit 1; }
[ -f .env ] || { err "missing .env at repo root — copy .env.prod.example to .env and fill it in"; exit 1; }

# --- preflight: required config (never prints secret values) ---
set -a; . ./.env; set +a
missing=0
need() { if [ -z "${!1:-}" ]; then err "missing required env: $1"; missing=1; fi; }
# Only auth is required to boot — connectors (Composio key, Shopify, stores) are
# configured in the dashboard Settings after launch.
need AUTH_MODE
need LOCAL_AUTH_TOKEN
_tok="${LOCAL_AUTH_TOKEN:-}"
if [ "${AUTH_MODE:-}" = "local" ] && [ "${#_tok}" -lt 50 ]; then
  err "LOCAL_AUTH_TOKEN must be >= 50 chars for AUTH_MODE=local"; missing=1
fi
[ -n "${COMPOSIO_API_KEY:-}" ] || info "COMPOSIO_API_KEY unset — set it in Settings after boot"
[ -n "${SHOPIFY_STORE_URL:-}${SHOPIFY_ACCESS_TOKEN:-}" ] || info "No Shopify config — add + connect a store in Settings (client id + secret)"
case "${CS_RUNTIME:-}" in
  llm|hermes)
    [ -n "${ANTHROPIC_API_KEY:-}" ] || info "CS_RUNTIME=$CS_RUNTIME but ANTHROPIC_API_KEY is unset — the LLM brain won't run"
    ;;
esac
[ "$missing" -eq 0 ] || { err "fix the missing config above, then re-run"; exit 1; }

PROFILE=()
QUICK=0
case "${QUICK_TUNNEL:-}" in 1|true|yes) QUICK=1 ;; esac
if [ -n "${TUNNEL_TOKEN:-}" ]; then
  PROFILE=(--profile tunnel)
  ok "Cloudflare Tunnel enabled (your hostname)"
elif [ "$QUICK" = 1 ]; then
  PROFILE=(--profile quicktunnel)
  ok "Cloudflare Quick Tunnel enabled (free public URL, no domain)"
else
  info "No tunnel — running locally on http://127.0.0.1:${PROXY_PORT:-8080} (set QUICK_TUNNEL=1 for a free public URL, or TUNNEL_TOKEN for your own domain)"
fi

info "Building + starting the stack…"
docker compose -f compose.yml -f compose.prod.yml --env-file .env "${PROFILE[@]}" up -d --build

# --- wait for health through the single-origin proxy ---
URL="http://127.0.0.1:${PROXY_PORT:-8080}/healthz"
info "Waiting for health at ${URL} …"
for _ in $(seq 1 60); do
  if curl -fsS -m 3 "$URL" >/dev/null 2>&1; then
    ok "Ecom-OS is up."
    info "Local:  http://127.0.0.1:${PROXY_PORT:-8080}"
    [ -n "${TUNNEL_TOKEN:-}" ] && info "Public: your Cloudflare Tunnel hostname (routes to http://proxy:80)"
    if [ "$QUICK" = 1 ]; then
      info "Fetching the free public URL…"
      PUB=""
      for _ in $(seq 1 20); do
        PUB="$(docker compose -f compose.yml -f compose.prod.yml logs quick-tunnel 2>/dev/null \
               | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)"
        [ -n "$PUB" ] && break
        sleep 2
      done
      [ -n "$PUB" ] && ok "Public URL: ${PUB}" || info "Public URL not ready yet — run ./scripts/deploy/tunnel-url.sh"
    fi
    info "Connections + CS readiness: GET /api/v1/ecom/connections (authed)"
    exit 0
  fi
  sleep 3
done
err "health check did not pass in time — inspect: docker compose -f compose.yml -f compose.prod.yml logs --tail=80"
exit 1
