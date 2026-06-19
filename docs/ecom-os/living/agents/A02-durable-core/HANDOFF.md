# A02 — Durable Events, Jobs, Traces, and Actions — Current Handoff

## Safe continuation point

Continue from the ready-for-integration A02 durable-core checkpoint on branch
`agent/a02-trace-ledger`. The next coherent step is either A06-facing frontend Activity
work after A06 primitives land or non-conflicting backend integration with A04/A05 once
their ports are ready.

## What is working

- SQLModel records and migration for durable inbox/outbox/jobs, traces/runs/spans/tool
  invocations, evidence/audit/incidents, and actions/attempts/state history.
- Service ports under `backend/app/events/`, `backend/app/jobs/`, `backend/app/traces/`,
  and `backend/app/actions/`.
- Focused invariant tests for duplicate event reuse, lease reclaim/dead-letter,
  transactional outbox dedupe/lease/reclaim/retry/dead-letter/delivered states,
  leased-job heartbeat/completion/concurrency-key blocking/retry behavior, trace/tool
  search, typed trace-search tool evidence filtering, role-filtered evidence, duplicate
  action intent reuse, exact action store/connection/actor/intent validation,
  conflicting action-intent digest rejection, `outcome_unknown` retry blocking, and
  reconciliation, including rejection of obvious secret-bearing action payload keys.
- Realtime email webhook POST now durably records an inbox event and leased job before
  scheduling the legacy CS loop; duplicate durable jobs do not reschedule the loop.
- Board webhook ingest now durably records an inbox event and leased job in the same
  transaction as payload/memory persistence before HTTP 202; duplicate provider event ids
  do not enqueue another legacy Redis/RQ delivery.
- Board webhook delivery can now use `process_durable_webhook_job` /
  `flush_durable_webhook_jobs`; it shares the existing notification behavior while
  recording durable success, retry, stale-target dead-letter, and attempt-cap dead-letter
  states.
- `WEBHOOK_DISPATCH_WORKER_MODE` controls worker rollout:
  - `legacy`: Redis/RQ only, default rollback mode.
  - `durable`: Postgres leased board-webhook jobs only.
  - `dual`: durable jobs first, then Redis/RQ compatibility tasks.
- `scripts/check_postgres_migration_upgrade.py` verifies full Alembic upgrade against a
  disposable PostgreSQL database. Latest run reached `a02d1e2f3a4b` and verified 14
  durable-core tables.
- Read-only trace/action Activity endpoints now expose durable state and role-filtered
  evidence:
  - `GET /activity/traces`
  - `GET /activity/traces/{trace_id}`
  - `GET /activity/actions`
  - `GET /activity/actions/{action_id}`
- `backend/app/traces/tools.py` exposes `trace_search_tool` for downstream
  agent/tool contexts. It returns trace summaries plus evidence only after server-side
  `ROLE_ACCESS` filtering; unknown roles receive public evidence only.
- Read-only incident diagnosis endpoints now expose incident state, optional root trace,
  root-trace actions, and role-filtered evidence:
  - `GET /activity/incidents`
  - `GET /activity/incidents/{incident_id}`
- Privileged audit Activity endpoints now expose audit diffs only to
  owner/admin/operator-equivalent roles:
  - `GET /activity/audit`
  - `GET /activity/audit/{audit_id}`
- Audit recording rejects before/after payloads with obvious secret-bearing keys such as
  `token`, `password`, `secret`, `credential`, `authorization`, or `api_key`.
- Tool invocation arguments/results, evidence metadata, action arguments/attempt
  summaries/reconciliation evidence, and audit diffs use the same obvious secret-key
  rejection at the durable boundary.

## What remains

- See `WORKBOARD.md`. The core is not yet wired into CS workflow execution, provider
  adapters, or frontend Activity surfaces.

## Blockers and decisions

- No hard blocker. A01/A04/A05/A06 interfaces remain pending; continue with local typed
  ports/fakes and record interface requests before cross-domain registration.

## Commands to resume

- `cd backend && uv run --extra dev python -m pytest tests/test_queue_worker_migration.py tests/test_webhook_dispatch.py tests/test_board_webhooks_api.py tests/test_realtime_webhook.py tests/test_durable_core.py`
- `make backend-lint`
- `cd backend && uv run --extra dev python scripts/check_migration_graph.py`
- `cd backend && A02_POSTGRES_TEST_DATABASE_URL=<empty disposable PostgreSQL URL> AUTH_MODE=local LOCAL_AUTH_TOKEN=<50+ chars> BASE_URL=http://localhost:8000 uv run --extra dev python scripts/check_postgres_migration_upgrade.py`

## Do not accidentally regress

- Do not remove or bypass the legacy Redis/RQ path until migration compatibility and
  rollback are proven; A09 owns compose removal.
- Do not treat `activity_events` or logs as trace coverage.
- Do not let any external-write caller start a connector attempt without an `Action`.
- Do not retry an action in `outcome_unknown` without reconciliation or manual
  resolution.
- Do not store secret/credential evidence, unredacted tool payloads, or audit diffs in
  trace/evidence/audit tables.
