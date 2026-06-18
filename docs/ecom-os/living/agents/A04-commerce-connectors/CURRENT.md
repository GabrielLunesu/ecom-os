---
owner: A04
branch: agent/a04-cs
status: implementing
last_verified_commit: SET_AFTER_CHECKPOINT_COMMIT
---

# A04 — Commerce Connectors and Read Models — Current State

## Mission

Build exact-bound connector adapters, signed ingestion, synchronization, normalized commerce read models, freshness/evidence, and Orders/Customers surfaces.

## Ownership

**Owns:** connection records and adapters (`backend/app/connectors/` + commerce/sync modules), webhook verification, Shopify/inbox synchronization, normalized stores/orders/customers/products/fulfilments/tracking and provider references, owned migrations (`A04*` prefix), `/orders`/`/customers`/connection-settings routes and read tools.

**Does not own:** ticket workflow/policy and autonomy (A05), durable action/inbox/job/trace internals (A02), identity/common types/generated client/lockfiles (A01), Hermes transport + tool catalog framework (A03), finance definitions (A08), UI primitives/shell/nav (A06), deploy/CI/secrets infra (A09).

## Current implementation

The repository is the OpenClaw/board-agent platform (FastAPI 0.131 + SQLModel/SQLAlchemy 2 async + Alembic) with an Ecom-OS prototype grafted on. The v2 commerce connector layer is now built under **`backend/app/connectors/`** (A04-owned), behind provider-independent contracts, with the prototype reused for transport only.

### v2 canonical (built this checkpoint — `backend/app/connectors/`)

- `errors.py` — typed, fail-closed connector errors (`ConnectorBindingError`, `ConnectorTimeout`→`outcome_unknown`, `ConnectorUnavailable`, `ConnectorRateLimited`, `WebhookVerificationError`, `CapabilityUnsupported`); redacted, classified, `retryable`/`outcome_confidence`.
- `binding.py` — `ConnectionBinding` exact brand/store/connection/account binding (I-09); rejects default/latest/empty; `from_connection` fails closed; `require_account` rejects wrong account.
- `ports.py` — `Coverage`/`Freshness`/`Evidence`/`ReadResult`/`ProviderCommand`/`AttemptResult`/`CapabilityDescriptor` and the `ConnectorPort` read/execute/reconcile ABC; `payload_hash`, `to_minor_units` (I-16). No provider payloads in contracts.
- `registry.py` — provider-independent `ConnectorRegistry`; `default_registry()` wires `direct/store` + `composio/inbox`; `composio/store` fails closed (managed OAuth pending, I-19).
- `adapters/` — `ShopifyCommerceAdapter` (normalizes raw Admin payloads, reads only), `InboxCommerceAdapter` (pinned Composio account, no first-ACTIVE), `FakeCommerceAdapter`/`FakeProviderBackend` (sandbox + failure fixtures).
- `models.py` + migration `a04commerce01` — normalized `commerce_connections/orders/order_lines/customers/products/fulfillments/provider_refs/sync_cursors` with source/external_id/source_updated_at/synced_at/coverage; money in minor units; plus A02 stand-in tables `commerce_provider_events` (durable inbox), `commerce_actions`/`commerce_action_attempts`.
- `webhooks.py` — HMAC raw-body verification (hex + Shopify base64) + `accept_webhook` (verify → durable insert → dedup-once); invalid signature never persisted.
- `durable.py` — `LocalDurableInbox` (A02 inbox stand-in) with `(source,account_ref,source_event_id)` dedup via SAVEPOINT.
- `sync.py` — `SyncEngine` initial + incremental + event-driven upsert; idempotent on natural key.
- `read_repository.py` — `CommerceReadRepository` (order by id/number/uuid, by customer, customer, stores) with freshness/coverage/evidence; outage → stale last-good.
- `actions.py` — `ActionExecutor` + `LocalDurableActionStore`: action digest + idempotency intent key, append-only attempts, `outcome_unknown` on timeout, reconciliation; duplicate intent never re-dispatches (I-06/07/08).
- `events.py` — normalized `MessageEvent` emission for A05 (untrusted, emitted once); A04 does not decide workflow.
- `tools.py` — read tool manifest + handlers (`ecom.store.list/order.get/order.search/customer.get`) returning result envelopes.
- `api.py` — commerce read router (`/api/v1/ecom/commerce/...`) with ok/degraded/404 states (pending central registration by A01/A09).

Evidence: `VERIFICATION.md` (33 A04 tests + 578-test full suite green; migration N-1 round-trip; mypy/ruff clean).

### Reused prototype (transport/secret handling only, kept behind v2)

- `services/connectors/secrets.py` (`Secret`/`ConnectionRef` redaction), `shopify_direct.py`, `composio_inbox.py`, `shopify_token.py`, `secret_store.py`, `board_webhooks.py` HMAC pattern (ported to commerce).

### Still conflicting / to retire

- `api/ecom_webhooks.py` (shared-secret, no durable inbox) — superseded by `connectors/webhooks.py`; retire when the email ingress route is migrated.
- Inbox first-ACTIVE discovery in `composio_inbox.discover_active_mail_account` — superseded by pinned `account_ref`; remove call sites during A05 integration.

### Canonical / reusable (keep behind v2 contracts)

- `backend/app/services/connectors/base.py` — `ShopifyConnector` ABC (`get_shop/get_order/search_orders/get_fulfillments/list_orders/create_discount`) and `InboxConnector` ABC. **Capability-shaped, Shopify-specific** — not yet a provider-independent port with a durable command/action envelope.
- `backend/app/services/connectors/secrets.py` — `Secret` (redacts in repr/str/format; `.reveal()` only) and `ConnectionRef` (frozen; `provider ∈ {composio,direct}`, rejects unknown). **Strong, keep.** `external_id` is overloaded (Composio account id vs. raw store domain) — insufficient for I-09 exact binding.
- `backend/app/services/connectors/shopify_direct.py` — `DirectShopifyConnector`, REST Admin `2025-01`, cursor pagination. Declared stopgap until managed OAuth; returns raw dicts (no normalization).
- `backend/app/services/connectors/shopify_token.py` — client-credentials + static-token cache (process memory only).
- `backend/app/services/connectors/registry.py` — `shopify_connector_for(ref)`; **`composio` branch raises `NotImplementedError`** (declared stub).
- `backend/app/services/connectors/composio_inbox.py` — Composio v3, **Outlook-only slugs**; `discover_active_mail_account()` picks first ACTIVE account → **violates I-09**.
- `backend/app/services/connectors/refunds.py` — `RefundExecutor`, approval-gated, distinct `SHOPIFY_REFUND_ACCESS_TOKEN` handle. Not a `ShopifyConnector` (capability-by-construction).
- `backend/app/api/board_webhooks.py` — **reference pattern**: HMAC-SHA256 over raw body (`_verify_webhook_signature` ~`:169`), size-capped `request.stream()`, durable `BoardWebhookPayload`, header redaction, rate/size limits. Owned by another lane (boards) — pattern to port, not edit.
- `backend/app/models/secret_entry.py` + `services/secret_store.py` — Fernet-encrypted secrets keyed by non-secret handle. Fernet key derived from `SECRETS_KEY`/`LOCAL_AUTH_TOKEN`.
- `backend/app/models/brand.py` — `Brand` (single-row) + `Store` (holds `provider/external_id/status` + operator profile; **no token column**). No first-class `Connection` entity.
- Tests: `tests/test_connector_invariants.py` (redaction/port-shape/refund-separation — will need rewrite when port shape changes), `test_shopify_token.py`, `test_connection_health.py`, `test_refund_path.py`, `test_ticket_ingestion.py`, `test_realtime_webhook.py`.

### Conflicts with v2 (must replace/redesign)

- `backend/app/api/ecom_webhooks.py` — commerce email webhook = **shared-secret token, no HMAC, no raw-body verification, no durable inbox, no idempotency**. Fire-and-forget trigger that re-runs the CS loop; content is pulled later via Composio polling. Opposite of `AGENTS.md`§4 / ADR-014.
- Connector calls are synchronous in-process `httpx` — **no durable action record, no idempotency key, no `outcome_unknown`** (violates I-06/I-07/I-08; writes must route through the A02 durable action port).
- Inbox account auto-discovery (first ACTIVE) — **violates I-09 exact account binding**.

### Absent (greenfield for v2)

- Normalized commerce model: `orders / order_lines / customers / products / variants / fulfillments / refunds / transactions / tracking / provider_refs` — none exist; data is fetched live and never persisted/normalized.
- First-class `connections` table decoupled from `stores`; persisted inbox connection.
- Initial/incremental **sync engine** (cursors, backfill, source/collected timestamps, freshness/coverage). Only `cs_loop.py` inbox polling exists.
- Cross-cutting read-model contract fields (source, source_updated_at, freshness_status, coverage_status, primary_trace_id) per BUILD §4.
- `/orders`, `/customers` pages; evidence-backed read tools (`ecom.order.search/get`, `ecom.customer.get`, `ecom.store.list`). Chat live-lookup is the only current read surface.

## Current architecture

See `DIAGRAMS.md` (Current vs Target). Today: React Chat → `/ecom/chat` → live `DirectShopifyConnector` REST calls returning raw dicts; KPIs computed on the fly in `metrics.py`; email webhook triggers a CS loop that polls Composio. No durable inbox, no normalized store of commerce truth, no exact-account binding on the inbox path.

## Dependencies

Consumes A01 (trace envelope, common money/time/ID/error types, generated client, central route registration), A02 (durable action + durable inbox/event ports, jobs, traces, evidence), A06 (UI token/component contract), A03 (tool catalog registration path — currently ungraphed). Exposes the **Connector adapter port**, ConnectionBinding, CommerceReadRepository, ProviderExecutionPort, ReconciliationAdapter, normalized sync/inbox events, and read-tool definitions to A02/A05/A08.

All consumed contracts are presently `proposed`/`not_started`; A04 proceeds behind typed local ports + fakes and files interface requests (see `INTERFACES.md` and `../../00-program/INTERFACE-REQUESTS.md`).
