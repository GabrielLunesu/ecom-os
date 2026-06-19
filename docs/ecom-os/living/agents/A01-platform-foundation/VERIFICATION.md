# A01 — Platform Foundation and Identity — Verification

## Latest verified commit

`64ca874` (branch `agent/a01-foundation`)

## Integration gates (A01-owned files)

| Gate | Command | Result |
|---|---|---|
| isort | `uv run isort --check-only <A01 files>` | pass |
| black | `uv run black --check <A01 files>` | pass (line-length 100) |
| flake8 | `uv run flake8 --config .flake8 <A01 files>` | pass (no findings) |
| mypy --strict | `uv run mypy` | pass — "no issues found in 216 source files" |
| migration graph | `uv run python scripts/check_migration_graph.py` | pass — single head `a01_0001_identity`, 35 revisions |
| migration N-1 (hermetic) | `pytest tests/test_identity_migration.py` | pass — upgrade/restart/downgrade from `a0b1c2d3e4f5` on seeded data |
| frontend prettier | `npx prettier --check src/api/generated/**` | pass |
| frontend eslint | `npx eslint src/api/generated` | pass |
| frontend tsc | `npx tsc --noEmit` | pass (exit 0) with regenerated client |

Notes / environment limits:
- `make backend-migration-check` runs upgrade→downgrade base→upgrade on a **Dockerized
  Postgres 16**; Docker is unavailable in this dev environment, so the Postgres run is
  deferred to CI/A09. The graph check + hermetic sqlite N-1 test cover the A01 migration.
- The repo baseline is **not** isort/black-clean: ~20 foreign-owned files
  (`app/services/*`, some prototype tests) fail `black --check`/`isort --check` at HEAD;
  A01 did not touch or reformat them (ownership). The whole-repo `make backend-format-check`
  is therefore red on pre-existing foreign violations, independent of A01.
- `scripts/ci/branch_readiness.py` is not present in this branch (A00/A09 tooling not yet
  merged); its constituent gates above are run directly.

## Original commit reference

`f92adbb` was the feature-complete commit; `64ca874` adds isort/black normalization.

## Environment

`cd backend && uv sync --extra dev` (Python 3.13.9 venv; dev extras carry pytest —
without `--extra dev`, `uv run pytest` falls back to a stray system pytest, which is the
"baseline broken" symptom to avoid).

## Required checks

| Check | Command | Result | Evidence |
|---|---|---|---|
| Lint | `uv run ruff check app` | **pass** | "All checks passed!" |
| Types | `uv run mypy app` | **pass** | "no issues found in 211 source files" |
| Full suite | `uv run pytest -q` | **628 passed, 1 xfailed** | 59.8s; baseline was 545 passed, 1 xfailed → +83, 0 regressions |
| Common types/errors | `uv run pytest tests/test_foundation_types.py` | 23 passed | UUIDv7 sortable, Money no-float/currency-guard, 15 error codes, outcome_unknown not retryable |
| Request/trace context | `tests/test_request_context.py` | 14 passed | W3C continue/fresh/malformed; ActorContext/StoreScope |
| Identity migration | `tests/test_identity_migration.py` | 3 passed | real Alembic upgrade/restart/downgrade on seeded user/brand/store |
| Owner bootstrap | `tests/test_owner_bootstrap.py` | 6 passed | anonymous→401, claim closes, idempotent reclaim, 2nd user→403 forbidden |
| Identity enforcement | `tests/test_identity_enforcement.py` | 11 passed | role/service/channel allowed+denied; channel role re-resolved (I-09) |
| Health primitives | `tests/test_health_primitives.py` | 4 passed | liveness/db/migrations dims; /readyz + /readyz/details |
| Contract + registry | `tests/test_contract_and_registry.py` | 6 passed | OpenAPI has ErrorEnvelope/ActorView/…; ErrorCode enum=15; /identity/me docs ErrorEnvelope |
| Secret redaction | `tests/test_secret_redaction.py` | 17 passed | log+error redaction; detection corpus finds no leak |

## Contract generation evidence

`uv run python backend/scripts/export_openapi.py` → `backend/openapi.json` (build
artifact, not committed). `cd frontend && npm ci && ORVAL_INPUT=<repo>/backend/openapi.json
npm run api:gen` regenerated `frontend/src/api/generated/**` (committed). Strict TS
produced: `model/errorEnvelope.ts` (→ `ErrorCode` enum, 15 members), `model/actorView.ts`
(→ `ActorType`), `bootstrapStatus.ts`, `ownerClaimResult.ts`, `healthReportResponse.ts`,
and `identity/identity.ts` hooks for the real `/identity/*` endpoints. `npm ci` did not
modify the A06-owned `package-lock.json`/`package.json`.

## Acceptance criteria (handoff)

- [x] Owner bootstrap closes after first owner; not replayable anonymously — `test_owner_bootstrap.py`.
- [x] Unauthorized HTTP operations fail server-side — anonymous 401 + non-owner 403 (typed).
- [x] Role, service, and channel fixtures cover allowed and denied paths — `test_identity_enforcement.py` + `app/auth/fixtures.py`.
- [x] No secret serialized/logged in A01 paths — `test_secret_redaction.py` corpus.
- [x] Common contracts generate strict frontend types used by a real endpoint — regenerated client + `/identity/me`.
- [x] Migration and restart pass against realistic seeded prototype data — `test_identity_migration.py`.

Socket-level denial and worker-lease recovery are owned by A02/A03; A01 provides the
identity/enforcement and DB-readiness primitives they build on.
