# A02 Durable Core v0

Operator-visible impact: none yet. This slice adds internal durable-core records and
service ports for future trace, incident, job, and action surfaces, adds read-only
Activity trace/action/audit APIs, and makes the realtime email webhook durable before it
starts customer-service work.

Engineering impact:

- Adds Postgres migration `a02d1e2f3a4b` for durable inbox/outbox/jobs, traces/runs/spans,
  tool invocations, evidence/audit/incidents, and action attempts/state history.
- Transactional outbox rows now include leased dispatch ownership and expiry fields so
  future dispatchers can claim due rows, skip active leases, reclaim expired leases, and
  record retry/dead-letter/delivered outcomes without duplicate delivery.
- Keeps legacy Redis/RQ queue helpers and existing webhook paths in place until migration
  compatibility and rollback are proven.
- Persists realtime email webhook triggers to `durable_inbox_events` and `durable_jobs`
  before scheduling the legacy CS loop; duplicate durable jobs do not trigger another
  loop.
- Persists board webhook triggers to `durable_inbox_events` and `durable_jobs` in the
  same transaction as payload/memory capture before returning HTTP 202; the existing
  Redis/RQ delivery queue is used only for newly created durable jobs.
- Adds durable board-webhook worker ports that process leased
  `board_webhook.payload.received` jobs through the existing notification behavior and
  persist success, retry, stale-target dead-letter, and attempt-cap dead-letter states.
- Adds `webhook_dispatch_worker_mode` with `legacy`, `durable`, and `dual` modes so
  operators can run Postgres durable webhook dispatch beside Redis/RQ and roll back to
  Redis/RQ-only behavior without code changes.
- Adds `scripts/check_postgres_migration_upgrade.py` for disposable PostgreSQL
  upgrade-to-head verification; latest run reached `a02d1e2f3a4b` and verified 14
  durable-core tables.
- Adds read-only `/activity/traces`, `/activity/traces/{trace_id}`,
  `/activity/actions`, `/activity/actions/{action_id}`, `/activity/incidents`, and
  `/activity/incidents/{incident_id}` contracts that return durable state and
  server-side role-filtered evidence.
- Adds a typed, read-only `trace_search_tool` contract for downstream agent/tool
  contexts. It returns trace summaries plus evidence only after server-side role/access
  filtering, with unknown roles limited to public evidence.
- Adds privileged read-only `/activity/audit` and `/activity/audit/{audit_id}` contracts
  for owner/admin/operator-equivalent roles, and rejects audit diffs containing obvious
  secret-bearing keys before storage.
- Rejects obvious secret-bearing keys in tool invocation arguments/results, evidence
  metadata, action normalized arguments, connector-attempt summaries, reconciliation
  evidence, and audit diffs before durable storage.
- Adds focused invariant tests for duplicate event acceptance, transactional outbox
  dedupe/lease/reclaim/retry/dead-letter/delivered states, lease reclaim, role-filtered
  evidence, leased-job heartbeat/completion/concurrency-key blocking/retry behavior,
  exact action binding validation, conflicting action-intent digest rejection, action
  intent idempotency, `outcome_unknown`, reconciliation, Activity trace/action detail
  filtering, trace-search tool evidence filtering, board webhook duplicate-provider-event
  suppression, durable worker retry/dead-letter behavior, incident diagnosis filtering,
  privileged audit reads, secret-bearing audit rejection, secret-bearing
  tool/evidence/action rejection, and queue migration/rollback worker modes.
