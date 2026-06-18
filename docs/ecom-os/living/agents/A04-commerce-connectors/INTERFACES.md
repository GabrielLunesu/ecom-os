# A04 — Commerce Connectors and Read Models — Interfaces

All A04 contracts are versioned `a04.<name>.vN`. Pre-implementation contracts are
`proposed`; they become `draft` when a typed port exists with a fake, and `stable` when
backed by tests and a migration. Provider payloads never appear in these contracts.

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `ConnectorRegistry` — resolve a provider-independent connector for an exact `ConnectionBinding` | a04.connector-registry.v1 / **draft (built+tested)** | `backend/app/connectors/registry.py` | A02, A05, A08 | Unknown provider/capability or unbound account → typed `CapabilityUnsupported`/`ConnectorBindingError`; never falls back to a default account |
| `ConnectionBinding` — `{brand_id, store_id, connection_id, provider, capability, account_ref, adapter_version}` | a04.connection-binding.v1 / **draft** | `backend/app/connectors/binding.py` | A02, A05, A08 | Missing/ambiguous field rejected closed (I-09) with traced reason, including in `unrestricted` mode |
| `ConnectorPort` (read/execute/reconcile) — reads return normalized records; writes carry `idempotency_intent_key`; returns evidence + `outcome_confidence` | a04.provider-exec.v1 / **draft** | `backend/app/connectors/ports.py` | A02 (drives durable action attempts) | Timeout-after-dispatch → `outcome_unknown`; never infers success from transport |
| `ReconciliationAdapter` — `ConnectorPort.reconcile`: query provider state by exact account + intent to resolve an ambiguous action | a04.reconciliation.v1 / **draft** | `backend/app/connectors/ports.py` + `actions.py` | A02 | Reconciler unhealthy → ambiguous retries paused; never rewrites the original attempt |
| `CommerceReadRepository` — normalized stores/orders/customers/products/fulfilments/tracking with source/freshness/coverage/evidence | a04.commerce-read.v1 / **draft** | `backend/app/connectors/read_repository.py` + `models.py` | A05, A08, read tools | Outage → last-good marked `stale`/`partial`; distinguishes not-found/unavailable/stale |
| Normalized **inbox/message events** | a04.commerce-events.v1 / **draft** | `backend/app/connectors/events.py` (`MessageEvent`, `ingest_inbox_messages`) | A05 | Idempotent by `(source, account, source_event_id)`; untrusted-flagged; A04 emits, A05 decides workflow |
| **Read tool definitions** — `ecom.store.list`, `ecom.order.search`, `ecom.order.get`, `ecom.customer.get` (read-only; freshness/coverage/evidence) | a04.read-tools.v1 / **draft** | `backend/app/connectors/tools.py` (`READ_TOOL_MANIFEST`); register via A03 | A03 catalog, A05 | No side effects beyond trace/audit; secret-free result envelopes |
| Commerce read API + `/orders`,`/customers`,connection-settings | a04.routes.v1 / **draft (API built; UI pending A06)** | `backend/app/connectors/api.py`; `frontend/src/app/(ecom)/...` (pending) | operator UI | API renders ok/degraded/404; UI states pending A06 primitives |

## Consumes

| Interface | Owner | Required version/status | Call sites | Fallback/degraded behavior |
|---|---|---|---|---|
| Durable **action** port (create/reuse action, record attempts, state machine, `outcome_unknown`) | A02 | proposed | every connector write | Typed local `DurableActionPort` fake until A02 ships; writes blocked behind flag |
| Durable **inbox/event** port (raw-body accept, unique provider key, outbox) | A02 | proposed (named "action port" in registry; inbox port to be disambiguated) | webhook ingress + sync emit | Local in-process inbox fake; do not ship commerce webhooks until real inbox exists |
| Trace context envelope (`trace_id`/coverage propagation) | A01/A02 | proposed | all tools, sync, webhooks | Local trace context shim; coverage defaults to `unknown` |
| Common money/time/ID/error types + generated API client + central route registration | A01 | proposed/not_started | models, routes, frontend client | Local typed copies marked provisional; request regeneration from A01 |
| UI token/component contract (shadcn/Radix) | A06 | proposed/not_started | `/orders`,`/customers`,connection settings | Build against placeholder primitives; no forked design system |
| Tool catalog registration framework | A03 | proposed/not_started; **edge A04→A03 missing in dependency graph** | read/write tool manifest | Export a manifest; file interface request (see below) |

## Open requests

Filed in `../../00-program/INTERFACE-REQUESTS.md` (IDs `IR-A04-01..05`). Do not create a
private competing contract here.
