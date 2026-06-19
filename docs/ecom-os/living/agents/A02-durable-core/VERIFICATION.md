# A02 — Durable Events, Jobs, Traces, and Actions — Verification

## Latest verified commit

`92fe0a9`

## Required checks

| Check | Command/fixture | Result | Evidence |
|---|---|---|---|
| Current-state audit | Read specs, parallel docs, A02 living docs, queue/activity/webhook/refund paths | complete | A02-owned `CURRENT.md`, `INTERFACES.md`, `RISKS.md`, `DIAGRAMS.md`, `WORKBOARD.md`, `HANDOFF.md`, and `VERIFICATION.md` updated. A00-owned docs were not edited. |
| Backend lint/format/type gate | `make backend-lint` | pass | `isort . --check-only --diff`: skipped 2 files; `black . --check --diff`: 302 files unchanged; `mypy`: success, no issues in 210 source files; `flake8 --config .flake8`: no findings. |
| Queue migration ownership cleanup | `cd backend && uv run --extra dev python -m pytest tests/test_queue_worker_migration.py` | pass | 5 passed in 44.14s after moving the rollout switch from shared A01-owned settings to worker-local `WEBHOOK_DISPATCH_WORKER_MODE`. |
| Unit/contract tests | `cd backend && uv run --extra dev python -m pytest tests/test_queue_worker_migration.py tests/test_webhook_dispatch.py tests/test_board_webhooks_api.py tests/test_realtime_webhook.py tests/test_durable_core.py` | pass | 47 passed in 96.44s after backend formatting. |
| Migration graph | `cd backend && uv run --extra dev python scripts/check_migration_graph.py` | pass | `OK: migration graph integrity passed`; head `a02d1e2f3a4b`; 35 reachable revisions. |
| PostgreSQL full migration upgrade | `cd backend && LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 A02_POSTGRES_TEST_DATABASE_URL=<empty disposable PostgreSQL URL> AUTH_MODE=local LOCAL_AUTH_TOKEN=<50+ chars> BASE_URL=http://localhost:8000 uv run --extra dev python scripts/check_postgres_migration_upgrade.py` | pass | `OK: PostgreSQL migration upgrade reached head`; revision `a02d1e2f3a4b`; durable tables verified: 14. |
| Programme migration make gate | `make backend-migration-check` | blocked locally | Graph check passed, then the fixture failed with `docker: command not found` and `make: *** [backend-migration-check] Error 127`. The direct disposable PostgreSQL verifier above passed. |
| Frontend gates | `make frontend-format-check`; `make frontend-lint`; `make frontend-typecheck` | skipped after user instruction | Earlier attempts did not pass in this worktree: Prettier reported existing frontend formatting diffs, `eslint` was not installed, and `tsc` was not installed. `make frontend-sync` / `npm install --no-audit --no-fund` was interrupted after hanging; user then instructed to skip this and finish. A02 changed no frontend files. |
| Branch readiness self-check | `python scripts/ci/branch_readiness.py agent/a02-trace-ledger`; `python3 scripts/ci/branch_readiness.py agent/a02-trace-ledger` | blocked locally | `python` is not on PATH. `python3` reports `scripts/ci/branch_readiness.py` does not exist in this worktree. |
| Integration/E2E | pending downstream adoption | not run | Frontend Activity surfaces and downstream CS/provider integration require A06/A05/A04 adoption. |

Replace stale results. Include exact failures; do not write “all good” without evidence.
