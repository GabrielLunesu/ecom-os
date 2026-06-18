# A01 — Platform Foundation and Identity — Current Handoff

## Safe continuation point

Commit `3909904` on branch `agent/a01-foundation`. Discovery + audit complete; living docs
are current truth; no A01 code changes made yet. Status: `discovery`. Next action is the
WORKBOARD "Next" slice 1 (common types + typed errors), with interface requests filed first.

## What is working (inherited prototype, audited)

- Auth seam (`app/core/auth.py`, `app/api/deps.py`) every router depends on.
- Clerk + local-static-token auth modes; agent (service) token auth with PBKDF2 hashing.
- Alembic at single head `a0b1c2d3e4f5`; startup auto-migrate.
- OpenAPI → orval → generated typed React-Query client.
- Fernet secret store (handle-addressed); structured logging; request-id middleware;
  `{detail,request_id}` error handler; rate limiting; security headers.
- ~90 backend pytest files (incl. auth/identity/security).

## What remains

See `WORKBOARD.md` (8 ordered slices) and the six handoff acceptance items. None started.

## Blockers and decisions

- Soft: A02 audit sink (use A01 no-op port/fake), A06 primitives (thin wrappers).
- Decision request: repo-layout conflict (RISKS A01-R09) — resolve before any directory move.
- Confirm coordination-doc (00-program) edit rights with A00 before filing into the registry.

## Commands to resume

```bash
cd backend
uv sync                       # restore locked deps
uv run alembic upgrade head   # expect head a0b1c2d3e4f5
uv run pytest                 # baseline suite
uv run ruff check . && uv run mypy app
# contract gen (needs running API on :8000):
python scripts/export_openapi.py   # then: cd ../frontend && npm run api:gen
```

## Do not accidentally regress

- The `deps.py` auth dependency seam — reshape behind it; do not break router contracts.
- Local auth must remain an explicit, documented dev/self-hosted mode (not removed).
- No big-bang folder rename (AGENTS.md §11; migration-map). Preserve passing tests.
- Invariants to hold from the first line of code: server-side authorization (AGENTS §7),
  exact identity/store binding (I-09), secrets never become ordinary data (I-15), money as
  integer minor units (I-16), UTC storage, every mutation auditable, trace context present.
