# A02 — Durable Events, Jobs, Traces, and Actions — Interfaces

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| EventInbox | v0 proposed | `backend/app/events/` | A03/A04/A05/A08/A09 | Duplicate source events return the existing accepted event; invalid verification is rejected before durable acceptance. |
| TransactionalOutbox | v0 proposed | `backend/app/events/` | A03/A04/A05/A07/A08/A09 | Duplicate dedupe keys reuse one row; dispatchers claim leased rows, expired leases are reclaimable, delivery failures remain durable and retryable/dead-lettered, and callers never perform external dispatch inside the business transaction. |
| LeasedJobQueue | v0 proposed | `backend/app/jobs/` | A03/A04/A05/A07/A08/A09 | Jobs are claimed with leases, heartbeat extends ownership, expiry permits reclaim, bounded retry creates visible dead letters. |
| Board webhook durable ingress | v0 compatibility | `backend/app/api/board_webhooks.py` | A03/A06/A09 | Ingest persists payload, memory, inbox event, and durable job transactionally before HTTP 202; legacy Redis enqueue runs only for a newly created durable job. |
| Board webhook durable worker | v0 compatibility | `backend/app/services/webhooks/dispatch.py`, `backend/app/services/webhooks/__init__.py` | A03/A09 | `process_durable_webhook_job` and `flush_durable_webhook_jobs` process leased `board_webhook.payload.received` jobs using the existing notification behavior, then complete, retry, or dead-letter the durable job. |
| Webhook worker migration mode | v0 compatibility | `backend/app/core/config.py`, `backend/app/services/queue_worker.py` | A09/operators | `legacy` drains only Redis/RQ, `durable` drains only Postgres leased webhook jobs, `dual` drains durable first then Redis/RQ; invalid values fall back to `legacy`. |
| PostgreSQL migration verifier | v0 evidence | `backend/scripts/check_postgres_migration_upgrade.py` | A00/A09/CI | Requires an empty disposable PostgreSQL database URL; refuses non-empty databases, upgrades to Alembic head, and verifies durable-core tables. |
| TraceRecorder | v0 proposed | `backend/app/traces/` | all | Missing observer data lowers coverage; Ecom-OS-controlled records are `verified`; logs are never treated as traces. |
| ToolInvocationRecorder | v0 proposed | `backend/app/traces/` | A03/A05/A07/A08 | Write-capable tools create an invocation before domain execution; schema/version mismatch fails before side effects; secret-bearing argument/result keys are rejected before storage. |
| ActionService | v0 proposed | `backend/app/actions/` | A04/A05/A08 | Duplicate intent reuses one action; missing actor/store/connection rejects; `outcome_unknown` blocks dangerous retry until reconciliation/manual resolution. |
| ReconciliationPort | v0 proposed | `backend/app/actions/` | A04/A05/A08 | Provider-specific reconciliation is injected by connector owners; action core records evidence/state transitions only. |
| EvidenceStore | v0 proposed | `backend/app/traces/` | all | Evidence search filters by server-side role/access label before content leaves the backend; secret labels and secret-bearing metadata keys are rejected before storage. |
| TraceSearchTool | v0 proposed | `backend/app/traces/tools.py` | A03/A05/A06/A07/A09 | Read-only typed contract returns trace summaries plus evidence already filtered by caller role; unknown roles receive public evidence only; invalid limits fail before query output. |
| AuditSink | v0 proposed | `backend/app/traces/` | A01/A03/A05/A06/A09 | Privileged/config changes append safe before/after diffs; records with obvious secret-bearing keys are rejected before storage. |
| IncidentService | v0 proposed | `backend/app/traces/` | A03/A05/A07/A09 | Incidents link traces/actions/evidence and distinguish verified findings from agent analysis. |
| Trace/Action/Incident/Audit Activity API | v0 proposed | `backend/app/api/activity.py`, `backend/app/schemas/traces.py` | A06/A09 | Read-only endpoints return durable trace/action/incident state, role-filtered evidence, and privileged audit records; missing records are 404; invalid trace coverage filter is rejected. |

## HTTP contracts

| Route | Response schema | Filters | Notes |
|---|---|---|---|
| `GET /activity/traces` | `DefaultLimitOffsetPage[TraceRead]` | `trace_type`, `entity_type`, `entity_id`, `status`, `coverage` | Requires user/agent auth; user callers must have active org membership until A01 supplies richer trace scope. |
| `GET /activity/traces/{trace_id}` | `TraceDetailRead` | none | Includes runs, spans, tool invocations, actions, and evidence linked to the trace tree after server-side access-label filtering. |
| `GET /activity/actions` | `DefaultLimitOffsetPage[ActionRead]` | `trace_id`, `state`, `action_type`, `target_type`, `target_id` | Lists durable action intents only; does not expose connector execution controls. |
| `GET /activity/actions/{action_id}` | `ActionDetailRead` | none | Includes attempts, state history, and evidence linked to the action after server-side access-label filtering. |
| `GET /activity/incidents` | `DefaultLimitOffsetPage[IncidentRead]` | `severity`, `status`, `detection_source`, `root_trace_id`, `suspected_cause_category`, `root_cause_confidence` | Lists incident summaries for operational diagnosis. |
| `GET /activity/incidents/{incident_id}` | `IncidentDetailRead` | none | Includes incident summary, optional root trace, root-trace actions, and evidence linked to the incident/trace/actions after server-side access-label filtering. |
| `GET /activity/audit` | `DefaultLimitOffsetPage[AuditRecordRead]` | `action`, `actor_type`, `actor_id`, `target_type`, `target_id`, `trace_id` | Requires owner/admin/operator-equivalent server-side role; lists privileged audit records only. |
| `GET /activity/audit/{audit_id}` | `AuditRecordRead` | none | Requires owner/admin/operator-equivalent server-side role; missing records are 404 and non-privileged callers receive 403. |

## Durable ingress contracts

| Ingress | Inbox event | Job | Compatibility behavior |
|---|---|---|---|
| Realtime email webhook | `event_type="realtime_email.trigger_received"`, `source="composio"`, `source_scope="realtime_email"` | `job_type="cs.realtime_email.received"` | Legacy CS background loop is scheduled only for a newly created durable job. |
| Board webhook ingest | `event_type="board_webhook.payload.received"`, `source="board_webhook"`, `source_scope="board:{board_id}:webhook:{webhook_id}"` | `job_type="board_webhook.payload.received"` | Legacy Redis/RQ `QueuedInboundDelivery` is enqueued only for a newly created durable job; duplicate provider event ids do not reschedule dispatch. |

## Durable worker contracts

| Worker port | Input | Success | Failure |
|---|---|---|---|
| `process_durable_webhook_job(session, job, worker_id=...)` | A leased `DurableJob` with `job_type="board_webhook.payload.received"` and `board_id`/`webhook_id`/`payload_id` payload fields | Calls the same board-agent notification path as legacy Redis/RQ dispatch and marks the job `succeeded`. | Malformed/stale target jobs become `dead_letter`; transient notification failures become `failed_retryable` until `max_attempts`, then `dead_letter`. |
| `flush_durable_webhook_jobs(worker_id=..., limit=..., lease_seconds=...)` | Claims only `board_webhook.payload.received` jobs from `LeasedJobQueue` | Commits claim and completion per batch item; returns successful completion count. | Failure state is persisted per job and processing continues to the next claimed item. |
| `claim_outbox_events(session, worker_id=..., topic=..., limit=..., lease_seconds=...)` | Pending or expired-leased `DurableOutboxEvent` rows due at or before `next_run_at` | Marks rows `leased`, binds `lease_owner`/`lease_expires_at`, and increments attempts for a dispatcher. | Active unexpired leases are skipped; `mark_outbox_failed` releases the lease into retry or `dead_letter`; wrong-worker completion/failure raises `OutboxLeaseError`. |

## Tool contracts

| Tool contract | Input | Output | Access behavior |
|---|---|---|---|
| `trace_search_tool(session, TraceSearchToolInput(...))` | `role`, trace/entity/status/coverage filters, `include_evidence`, `limit` | `TraceSearchToolResult` with `TraceRead` summaries and `EvidenceRead` rows | Evidence is collected from trace/run/span/tool-invocation/action targets and filtered through `ROLE_ACCESS` before returning; unknown roles fall back to public evidence only. |

## Queue migration modes

| `webhook_dispatch_worker_mode` | Behavior | Rollout use |
|---|---|---|
| `legacy` | `queue_worker.flush_queue` skips durable jobs and drains Redis/RQ only. | Default and rollback mode while Redis/RQ compatibility remains in place. |
| `durable` | `queue_worker.flush_queue` claims `board_webhook.payload.received` durable jobs only and idles without Redis polling when empty. | Postgres-only trial mode before A09 removes Redis. |
| `dual` | `queue_worker.flush_queue` runs durable webhook jobs first, then drains Redis/RQ compatibility tasks. | Coexistence mode for staged migration and replay comparison. |

## Migration verification

Run `scripts/check_postgres_migration_upgrade.py` with
`A02_POSTGRES_TEST_DATABASE_URL` pointed at an empty disposable PostgreSQL database. The
script refuses non-empty databases, runs Alembic `upgrade head`, verifies the head
revision, and checks required durable-core tables exist.

## Consumes

| Interface | Owner | Required version/status | Call sites | Fallback/degraded behavior |
|---|---|---|---|---|
| Identity/request context | A01 | pending | actor fields on inbox/jobs/traces/actions/audit | Store explicit `actor_type`/`actor_id` strings until A01 typed context lands. |
| Connector execution/reconciliation port | A04 | pending | `ActionService` attempt execution and reconciliation callbacks | Use fakes in A02 tests; no provider adapter implementation in A02. |
| CS action schemas/grants/approvals | A05 | pending | action type, approval and autonomy fields | Generic action fields accept frozen normalized arguments; A05 owns policy semantics. |
| UI primitives | A06 | pending | `/activity`, trace detail, incident detail routes | Backend/search contracts proceed; frontend route shells wait for A06 primitives. |

## Open requests

Cross-domain requests also appear in `../../00-program/INTERFACE-REQUESTS.md`. Do not
create a private competing contract here.
