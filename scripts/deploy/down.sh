#!/usr/bin/env bash
# Stop the Ecom-OS production stack. Pass --volumes to also drop the database.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
EXTRA=()
[ "${1:-}" = "--volumes" ] && EXTRA=(--volumes)
docker compose -f compose.yml -f compose.prod.yml --profile tunnel --env-file .env down "${EXTRA[@]}"
