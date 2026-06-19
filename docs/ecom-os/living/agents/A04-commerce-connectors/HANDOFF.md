# A04 — Commerce Connectors and Read Models — Current Handoff

## Safe continuation point

`agent/a04-cs` at the recorded checkpoint (`CURRENT.md last_verified_commit`). The v2
connector layer is built under `backend/app/connectors/` with migration `a04c0de01`
and 33 passing A04 tests; the full suite (578) is green and mypy/ruff are clean. No other
agent's source was modified; cross-domain needs are filed as `IR-A04-01..05`.

## What is working (built + tested)

- Exact-bound, provider-independent connector ports + registry; Shopify/inbox/fake adapters.
- Signed raw-body webhook verification → durable inbox with dedup-once.
- Normalized commerce model + idempotent initial/incremental/event sync.
- Evidence-backed read repository + read tools; outage → stale last-good.
- Durable write path (action digest + intent key, attempts, `outcome_unknown`, reconciliation).
- Normalized inbox/message events for A05; commerce read API.
- See `VERIFICATION.md` for the exact acceptance→test mapping.

## What remains

- See `WORKBOARD.md` "Next (integration-dependent)": swap A02 stand-ins, central
  registration (A01/A09/A03), A06 UI pages, retire legacy email webhook, live Shopify
  write conformance.

## Blockers and decisions

- Consumed contracts A02/A06/A03 are `proposed`/`not_started`; built behind typed local
  ports + fakes. Decision pending with A02: register a distinct durable **inbox** port
  vs. the single "Durable action port" (IR-A04-01).

## Commands to resume

```
cd backend && uv sync --extra dev
uv run pytest tests/test_a04_*.py -q          # A04 suite (33)
uv run mypy app/connectors                    # type check
uv run python scripts/check_migration_graph.py
# migration N-1 round-trip (sqlite):
DATABASE_URL=sqlite:////tmp/a04.sqlite AUTH_MODE=local \
  LOCAL_AUTH_TOKEN=test-... BASE_URL=http://localhost:8000 \
  uv run alembic stamp a0b1c2d3e4f5 && uv run alembic upgrade head && uv run alembic downgrade a0b1c2d3e4f5
```

Branch: stay on `agent/a04-cs` (docs elsewhere name `agent/A04-commerce-connectors`; do not switch).

## Do not accidentally regress

- I-09 exact account binding: never reintroduce default/latest/first-ACTIVE selection.
- I-07/I-08: keep `(source,account,event_id)` and `idempotency_intent_key` uniqueness;
  never re-dispatch an `outcome_unknown` action without reconciliation.
- I-15: `Connection` stores references only; keep `Secret` redaction; refund executor
  stays out of the read connector surface.
- Provider payloads stay evidence — never serialize raw provider dicts into public contracts.
- Durable-insert-before-process: webhooks persist before any processing.
