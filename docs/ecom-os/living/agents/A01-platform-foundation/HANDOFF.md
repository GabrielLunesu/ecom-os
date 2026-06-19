# A01 — Platform Foundation and Identity — Current Handoff

## Safe continuation point

Commit `f92adbb` on branch `agent/a01-foundation`. Eight tested foundation slices are
implemented and committed; full suite green (628 passed, 1 xfailed); ruff + mypy clean
(211 files). Status: `verification` → ready to mark `ready_for_integration` after the
interface requests are filed. No prototype behaviour was removed; everything is additive
behind stable seams.

## What is working (A01-delivered)

- Common types: `app/core/{ids,money,time}.py`; typed errors `app/core/errors.py` +
  handler.
- Request/actor/store/trace context `app/core/context.py` + W3C propagation middleware.
- Identity schema + migration `a01_0001_identity_foundation` (single head).
- Owner bootstrap that closes (`app/auth/bootstrap.py`, `app/api/identity.py`); role
  seeding; service & channel identity verification; enforcement deps; fixtures.
- Health primitives `/readyz` + `/readyz/details`.
- Route registry `app/api/registry.py`; regenerated strict TS client.
- Secret redaction at log + error boundaries + detection corpus.
- A02 audit/trace sink port (no-op default) in `app/auth/audit.py`.

## What remains

- File interface requests (INTERFACES.md): A02 audit-sink shape, A06 identity-UI
  primitives, A09 contract/migration workflow, A03 `Gateway.token` redaction.
- Deferred (need a consuming vertical): retrofit prototype money/timestamps (R02/R03);
  recent-auth step-up hook (`05-OPS` §3.2); swap no-op audit sink for A02's.
- Resolve repo-layout decision request (R09).

## Commands to resume

```bash
cd backend
uv sync --extra dev            # dev extras carry pytest (else stray system pytest runs)
uv run alembic upgrade head    # head: a01_0001_identity
uv run ruff check app && uv run mypy app
uv run pytest -q               # expect 628 passed, 1 xfailed
# contract regen:
uv run python scripts/export_openapi.py
cd ../frontend && npm ci && ORVAL_INPUT="$(pwd)/../backend/openapi.json" npm run api:gen
```

## Do not accidentally regress

- The `app/api/deps.py` and `app/core/auth.py` auth seams — reshape behind them.
- Local auth stays an explicit dev/self-hosted mode (documented limits), not removed.
- No big-bang folder rename (AGENTS §11). Additive only.
- Invariants held from the first line: server-side authorization (§7), exact
  identity/store binding (I-09), secrets never ordinary data (I-15), Money as integer
  minor units (I-16), UTC storage, trace context present, owner bootstrap closes.
- `uuid7()` for NEW tables; do not retrofit prototype `uuid4` tables casually.
