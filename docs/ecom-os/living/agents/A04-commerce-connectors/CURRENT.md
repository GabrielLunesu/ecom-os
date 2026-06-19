---
owner: A04
branch: agent/a04-cs
status: ready_for_integration
last_verified_commit: 26481bfbceae85bedcae28fb3d4d62d05d5a2d59
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
- `models.py` + migration `a04c0de01` — normalized `commerce_connections/orders/order_lines/customers/products/fulfillments/provider_refs/sync_cursors` with source/external_id/source_updated_at/synced_at/coverage; money in minor units; plus A02 stand-in tables `commerce_provider_events` (durable inbox), `commerce_actions`/`commerce_action_attempts`.
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

### Not yet migrated onto v2 (greenfield items now superseded by the layer above)

- Legacy live-read paths (`metrics.py`, `services/chat.py`) still call `DirectShopifyConnector` directly for raw dicts; migrate to `CommerceReadRepository` during A05/A08 integration.
- `/orders`,`/customers` React pages do not exist yet (pending A06 primitives, IR-A04-04); the backend read API + tools that power them are built.

## Current architecture

See `DIAGRAMS.md` (Target diagram is now the implemented shape). v2 path: signed webhook → `connectors/webhooks.accept_webhook` → `LocalDurableInbox` (dedup-once) → `SyncEngine` upsert into normalized models → `CommerceReadRepository`/read tools/`api.py` serve evidence-backed reads; external writes go `ActionExecutor` → `ConnectorPort.execute` → durable action+attempts with `outcome_unknown`/reconcile. Exact `ConnectionBinding` gates every call. Legacy live-lookup chat/metrics remain until migrated.

## Dependencies

Consumes A01 (trace envelope, common money/time/ID/error types, generated client, central route registration), A02 (durable action + durable inbox/event ports, jobs, traces, evidence), A06 (UI token/component contract), A03 (tool catalog registration path — currently ungraphed). Exposes the **Connector adapter port**, ConnectionBinding, CommerceReadRepository, ProviderExecutionPort, ReconciliationAdapter, normalized sync/inbox events, and read-tool definitions to A02/A05/A08.

All consumed contracts are presently `proposed`/`not_started`; A04 proceeds behind typed local ports + fakes and records its cross-domain needs in `INTERFACES.md` ("Cross-domain needs"). A04 does not edit `00-program/**`.
