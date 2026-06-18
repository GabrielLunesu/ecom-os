# A01 — Platform Foundation and Identity — Verification

## Latest verified commit

`3909904580732c27a9c6821ef44487c706d6a180` (discovery/audit only; no A01 code changes yet)

## Status

Discovery complete. No A01 implementation has run, so all required checks are **not run**.
The table below is the plan; results are filled as slices land.

| Check | Command/fixture | Result | Evidence |
|---|---|---|---|
| Static/type checks | `cd backend && uv run ruff check . && uv run mypy app` | not run | — |
| Unit/contract tests | `cd backend && uv run pytest` (existing ~90 files baseline) | not run | — |
| Money/types invariants | new tests: no-float Money, currency guard, UUIDv7 sortable, UTC round-trip | not run | — |
| Typed error envelope | new test: 15 codes serialize `{code,message,retryable,trace_id}`; ≥1 real endpoint | not run | — |
| Server-side denial | new fixtures: role/service/channel allowed+denied; cross-store denial | not run | — |
| Owner bootstrap closure | new test: first owner created, anonymous replay → `forbidden`, host-only reopen | not run | — |
| Migration/rollback | `alembic upgrade head` + N-1 fixture on realistic seeded data; restart recovery | not run | — |
| Health primitives | new test: liveness vs readiness(read/run/write) distinct; DB/queue probes | not run | — |
| Secret redaction | secret-detection corpus over logs/traces/responses (incl. `Gateway.token`) | not run | — |

## Baseline observations (read-only, at 3909904)

- Single linear Alembic head: `a0b1c2d3e4f5` (`add_store_profile`).
- Contract pipeline exists: `scripts/export_openapi.py` → `openapi.json` → orval →
  `frontend/src/api/generated`.
- Backend lock: `backend/uv.lock`; Python ≥3.12; fastapi 0.131.0, sqlalchemy 2.0.46,
  sqlmodel 0.0.32, alembic 1.18.3.

Replace stale results with exact latest evidence. Include exact failures; do not write
"all good" without evidence.
