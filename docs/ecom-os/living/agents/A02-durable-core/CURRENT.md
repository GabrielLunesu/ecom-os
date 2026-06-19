---
owner: A02
branch: agent/a02-trace-ledger
status: ready_for_integration
last_verified_commit: 5c78fcc
---

# A02 — Durable Events, Jobs, Traces, and Actions — Current State

## Mission

Build the Postgres durable operational core: inbox/outbox, leased jobs, traces, actions, evidence, incidents, reconciliation primitives, and Activity surfaces.

## Ownership

**Owns:** events, Postgres jobs, traces/runs/spans/tool invocations, actions/attempts/state history, evidence/audit/incidents, trace search tools and Activity/trace/incident routes.

**Does not own:** provider adapters, business-specific CS policy, Hermes transports, metric formulas, deployment files.

## Current implementation

Audited on branch `agent/a02-trace-ledger`; latest verified implementation commit is
`5c78fcc`.

- Existing queue behavior is a Redis/RQ compatibility path in `backend/app/services/queue.py` and `backend/app/services/webhooks/queue.py`. It supports JSON envelopes, delayed scheduling, attempts, and legacy payload decoding. It remains in place for compatibility, but realtime email and board webhook ingress now create Postgres durable jobs before the legacy queue path is used. Board webhook delivery also has an additive durable worker path in `backend/app/services/webhooks/dispatch.py`.
- Queue worker migration is controlled by the worker-local `WEBHOOK_DISPATCH_WORKER_MODE` environment variable in `backend/app/services/queue_worker.py`:
  - `legacy` keeps the existing Redis/RQ-only worker behavior and is the default rollback mode.
  - `durable` processes only Postgres leased board-webhook jobs.
  - `dual` processes durable board-webhook jobs first, then drains the Redis/RQ compatibility queue.
  Invalid values fall back to `legacy`.
- Existing realtime email webhook ingress is now partially migrated in `backend/app/api/ecom_webhooks.py`: after shared-secret authentication, POST requests persist a `DurableInboxEvent` and `DurableJob`, commit them, then schedule the legacy CS loop only for a newly created durable job. This preserves compatibility while preventing in-memory-only acceptance for that route.
- Existing board webhook persistence uses `board_webhooks` and `board_webhook_payloads` models/migrations. Board webhook ingest now also creates a `DurableInboxEvent` and `DurableJob` inside the same transaction as payload/memory persistence before returning HTTP 202. Provider event headers (`x-webhook-event-id`, `x-event-id`, `x-request-id`, `x-github-delivery`, `x-shopify-webhook-id`) are used as the durable source event id when present; otherwise the compatibility payload id is used as the fallback event id. The legacy Redis/RQ delivery enqueue still runs only when a new durable job is created.
- Existing activity is `backend/app/models/activity_events.py`, `backend/app/services/activity_log.py`, and `backend/app/api/activity.py`. This is a board/task feed with access filtering; it is not a trace/run/span/action/evidence ledger.
- Existing ticket evidence/audit is local to tickets in `backend/app/models/tickets.py`. It is not a cross-domain evidence/audit model.
- Existing refund execution in `backend/app/services/refunds.py` and `backend/app/services/connectors/refunds.py` is approval-gated and records failures on `refund_requests`, but it bypasses the v2 action intent/attempt/outcome-unknown contract. Refund execution remains outside A02 implementation scope; A02 will provide generic action primitives only.
- Canonical v0 A02 primitives now exist under `backend/app/events/`, `backend/app/jobs/`, `backend/app/traces/`, and `backend/app/actions/`. They are additive service ports. The TransactionalOutbox supports deduplication, leasing, expired-lease reclaim, bounded retry, dead-letter, and delivered states for future dispatchers. `backend/app/traces/tools.py` exposes a typed, read-only `trace_search_tool` contract for downstream agents; it searches durable traces and filters evidence by server-side role before returning model/tool context. Realtime email webhook ingress and board webhook ingest are wired to the durable inbox/job path; board webhook delivery can now be processed by `process_durable_webhook_job` / `flush_durable_webhook_jobs` with leased-job success, retry, and dead-letter state. CS workflow execution, provider adapters, and frontend surfaces still need migration.
- New durable SQLModel records are in `backend/app/models/events.py`, `backend/app/models/traces.py`, and `backend/app/models/actions.py`, with migration `backend/migrations/versions/a02d1e2f3a4b_add_durable_core_tables.py`.
- Activity now exposes read-only trace/action/audit discovery contracts from the A02-owned `backend/app/api/activity.py` router:
  - `GET /activity/traces`
  - `GET /activity/traces/{trace_id}`
  - `GET /activity/actions`
  - `GET /activity/actions/{action_id}`
  - `GET /activity/incidents`
  - `GET /activity/incidents/{incident_id}`
  - `GET /activity/audit`
  - `GET /activity/audit/{audit_id}`
  These endpoints return durable trace/action/incident state, server-side role-filtered evidence, and privileged audit records for owner/admin/operator roles. They do not infer action success from transport status, logs, or model text.
- Tool invocation recording, tool result recording, evidence metadata recording, audit recording, action intent creation, connector-attempt summaries, and reconciliation evidence reject payloads containing obvious secret-bearing keys such as `token`, `password`, `secret`, `credential`, `authorization`, or `api_key`; callers must pass redacted operational data and safe evidence.
- Focused invariant coverage is in `backend/tests/test_durable_core.py`: duplicate inbox event reuse, transactional outbox dedupe/lease/reclaim/retry/dead-letter/delivered states, invalid verification rejection, leased-job heartbeat/completion/concurrency-key blocking/retry/reclaim/dead-letter behavior, verified trace/tool search, role-filtered evidence, typed trace-search tool filtering before agent context, secret-bearing tool/evidence/audit/action rejection, exact action store/connection/actor/intent validation, conflicting action-intent digest rejection, duplicate action intent reuse, `outcome_unknown` retry blocking, reconciliation, trace/action Activity contract filtering, incident diagnosis filtering, and privileged audit reads. Realtime webhook compatibility coverage is in `backend/tests/test_realtime_webhook.py`. Board webhook compatibility/durable-ingress coverage is in `backend/tests/test_board_webhooks_api.py`. Durable and Redis/RQ webhook dispatch compatibility coverage is in `backend/tests/test_webhook_dispatch.py`. Queue worker migration/rollback mode coverage is in `backend/tests/test_queue_worker_migration.py`.

## Current architecture

Current and target architecture are documented in `DIAGRAMS.md`. The legacy path is preserved as compatibility input while A02 adds Postgres-backed durable-core primitives beside it. A09 owns final Redis compose removal after compatibility and rollback are proven.

## Dependencies

Consumes pending A01 identity/request context and A06 UI primitives. Until those are accepted, A02 records typed actor/store/connection fields directly and exposes local service ports/fakes. Exposes EventInbox, Outbox, LeasedJobQueue, TraceRecorder, ToolInvocationRecorder, ActionService, EvidenceStore, AuditSink, IncidentService, and TraceSearch contracts to A03-A09. Provider/refund execution remains outside A02 scope and must adopt ActionService through A04/A05 before those writes can claim v2 action coverage.
