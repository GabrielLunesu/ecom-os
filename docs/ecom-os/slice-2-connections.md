# Ecom-OS — Slice 2: Connections, data model, bootstrap gate

Implements Build Spec §1.5, §4 (brand→stores), §5 (connectors), and Invariants 1, 2, 5
(security-critical → tests-first).

## What shipped
- **Connector layer** (`backend/app/services/connectors/`):
  - `Secret` wrapper — repr/str/format are always redacted; value only via `.reveal()`
    at the request boundary (Invariant 5).
  - `ConnectionRef` (provider + external id) — the only thing persisted; never creds
    (Invariant 1). `resolve_secret()` / `env_or_setting()` read values from env →
    Settings at call time.
  - `ShopifyConnector` interface = reads + `create_discount`, **no refund method by
    construction**; `RefundExecutor` is a separate, approval-gated path with its own
    scoped handle (Invariant 2). `DirectShopifyConnector` talks Admin REST.
  - `ComposioInboxConnector` for the Outlook/Gmail support inbox.
- **Bootstrap gate** (`connection_health.py`) — confirms Shopify + inbox live and
  refuses the CS loop until both are (`assert_ready_for_cs_loop`). Verified live.
- **Data model** — `brands` + `stores` tables (`models/brand.py`, migration
  `d1e2c3b4a5f6`). A store row holds a connection ref only. `services/stores.py`
  seeds the brand + env-configured store idempotently.
- **API** — authed `GET /api/v1/ecom/connections` and `GET /api/v1/ecom/stores`
  (provider/status/ref only, no secrets).
- **Frontend** — `lib/ecom-api.ts` hooks; the global store switcher now reads real
  stores; Settings reshaped in-shell (`(ecom)/settings`) showing live connection
  status + stores. (Old per-user `/settings` profile page removed; profile returns
  in the Team slice.)

## Verify
- `cd backend && uv run pytest tests/test_connector_invariants.py tests/test_connection_health.py` → 14 pass.
- `uv run mypy app/services/connectors app/services/stores.py app/api/ecom.py` → clean.
- Live: `/api/v1/ecom/connections` → both providers connected; `/api/v1/ecom/stores`
  → seeded store `stv0xe-c4.myshopify.com` (status connected).
- `cd frontend && npm run build` → succeeds.

## Local dev (no Docker)
Project-local Postgres at `./.localdb`; `backend/.env` + `frontend/.env.local`
(both gitignored). See `docs/ecom-os/bootstrap.md`.
