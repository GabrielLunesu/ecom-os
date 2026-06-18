#!/usr/bin/env bash
# Print the current free Cloudflare Quick Tunnel public URL (if running).
# The URL changes whenever the quick tunnel restarts.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
URL="$(docker compose -f compose.yml -f compose.prod.yml logs quick-tunnel 2>/dev/null \
       | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)"
if [ -n "$URL" ]; then
  echo "$URL"
else
  echo "No quick-tunnel URL found. Start it with: QUICK_TUNNEL=1 ./scripts/deploy/up.sh" >&2
  exit 1
fi
