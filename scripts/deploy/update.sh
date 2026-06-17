#!/usr/bin/env bash
# Ecom-OS self-update: pull the latest code, rebuild, and restart in place.
# The Hermes agent runs this to update a stale deployment. Data (Postgres volume)
# and .env are preserved; migrations apply on boot (DB_AUTO_MIGRATE).
#
#   ./scripts/deploy/update.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

info() { printf '• %s\n' "$*"; }
ok() { printf '\033[32m✓ %s\033[0m\n' "$*"; }

command -v git >/dev/null || { echo "git not found"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose v2 not found"; exit 1; }
[ -f .env ] || { echo "missing .env — run ./scripts/deploy/up.sh first"; exit 1; }

BEFORE="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
info "Current version: ${BEFORE}"

# Pull the latest from the default branch (public repo — no token needed).
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
info "Pulling origin/${BRANCH} …"
git fetch --quiet origin "$BRANCH"
git merge --ff-only "origin/${BRANCH}" || {
  echo "fast-forward failed — local changes present. Stash/commit them, then re-run." >&2
  exit 1
}
AFTER="$(git rev-parse --short HEAD)"

if [ "$BEFORE" = "$AFTER" ]; then
  ok "Already up to date (${AFTER}). Nothing to rebuild."
  exit 0
fi
info "Updated ${BEFORE} -> ${AFTER}. Rebuilding…"

PROFILE=()
[ -n "$(grep -E '^TUNNEL_TOKEN=.+' .env 2>/dev/null || true)" ] && PROFILE=(--profile tunnel)

# Rebuild changed images and recreate; migrations run on backend boot.
docker compose -f compose.yml -f compose.prod.yml --env-file .env "${PROFILE[@]}" up -d --build

# Wait for health through the proxy.
PORT="$(grep -E '^PROXY_PORT=' .env | cut -d= -f2- || true)"; PORT="${PORT:-8080}"
for _ in $(seq 1 60); do
  if curl -fsS -m 3 "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
    ok "Updated to ${AFTER} and healthy."
    exit 0
  fi
  sleep 3
done
echo "updated but health check did not pass — check: docker compose -f compose.yml -f compose.prod.yml logs --tail=80" >&2
exit 1
