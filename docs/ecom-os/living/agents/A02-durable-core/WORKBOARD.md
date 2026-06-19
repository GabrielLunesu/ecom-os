# A02 — Durable Events, Jobs, Traces, and Actions — Workboard

## Implemented and verified

- Evidence-based current-state audit published in `CURRENT.md`.
- Initial v0 interface inventory published in `INTERFACES.md`.
- Added v0 durable-core SQLModel records, migration, and service ports for inbox/outbox, leased jobs, traces/tool invocations, evidence/audit/incidents, and actions/attempts.
- TransactionalOutbox now supports dedupe, leased claims, expired-lease reclaim, retry scheduling, dead-letter, wrong-worker rejection, and delivered states.
- Added typed role-filtered `trace_search_tool` in `backend/app/traces/tools.py` for downstream agent/tool contexts.
- Tool invocation arguments/results, evidence metadata, action arguments/attempt summaries/reconciliation evidence, and audit diffs now reject obvious secret-bearing keys before durable storage.
- Added focused invariant tests in `backend/tests/test_durable_core.py`, including transactional outbox dedupe/lease/reclaim/retry/dead-letter/delivered states, leased-job heartbeat/completion/concurrency-key blocking/retry behavior, trace-search tool evidence filtering, secret-bearing tool/evidence/action/audit rejection, and exact action binding/conflicting-intent rejection; latest run passed.
- Realtime email webhook now persists `DurableInboxEvent` and `DurableJob` before scheduling the legacy CS loop; duplicates do not reschedule the loop.
- Added read-only `/activity/traces`, `/activity/traces/{trace_id}`, `/activity/actions`, and `/activity/actions/{action_id}` contracts with server-side evidence access filtering.
- Added read-only `/activity/incidents` and `/activity/incidents/{incident_id}` diagnosis contracts with root trace, related action, and role-filtered evidence context.
- Added privileged read-only `/activity/audit` and `/activity/audit/{audit_id}` contracts for owner/admin/operator-equivalent roles, plus recorder rejection for audit before/after payloads containing obvious secret-bearing keys.
- Board webhook ingest now persists `BoardWebhookPayload`, `BoardMemory`, `DurableInboxEvent`, and `DurableJob` transactionally before HTTP 202; the legacy Redis/RQ delivery enqueue runs only for a newly created durable job, so duplicate provider event ids do not reschedule dispatch.
- Board webhook delivery now has a durable worker port: `process_durable_webhook_job` / `flush_durable_webhook_jobs` claim only `board_webhook.payload.received` jobs and persist success, retry, stale-job dead-letter, and attempt-cap dead-letter states.
- Queue worker migration modes now exist and are covered: `legacy` is the default rollback path, `durable` processes only Postgres leased webhook jobs, and `dual` processes durable jobs first then Redis/RQ compatibility tasks.
- Supported Postgres migration upgrade evidence now exists via `backend/scripts/check_postgres_migration_upgrade.py`; a disposable local Postgres cluster upgraded to head `a02d1e2f3a4b` and verified all 14 durable-core tables.

## Now

- Ready for integration review. Build frontend Activity surfaces after A06 primitives are accepted, or continue non-conflicting backend integration with A05/A04 ports once those interfaces are available.

## Next

- Keep A02 evidence current while downstream CS/provider/frontend branches adopt the durable ports.

## Blocked

- Not blocked. A01/A04/A05/A06 contracts are pending, but local typed ports/fakes allow progress.

## Exit condition

Branch exit requires Build Spec Slice 2 acceptance: duplicate events accepted once; expired leases recover; seeded run/action searchable by primary entity keys; coverage labels are honest; restricted evidence is filtered server-side; and legacy Redis/RQ behavior has a tested compatibility/migration path before A09 removes Redis.
