# A02 — Durable Events, Jobs, Traces, and Actions Handoff

**Branch:** `agent/A02-durable-core`

## Mission

Build the durable operational spine that makes high-volume agent work replayable, traceable, idempotent, and diagnosable.

## Required reading

Read root `AGENTS.md`; all normative files in `docs/ecom-os/specs/`; all files in
`docs/ecom-os/parallel-build/`; all programme living docs; every agent's `CURRENT.md` and
`INTERFACES.md`; then inspect the current implementation and Git history for this domain.
The normative v2 documents beat old READMEs and old implementation assumptions.

## Working method

Work on the assigned branch/worktree. Before substantial code, replace placeholders in
your living docs with an evidence-based current-state map, interfaces, risks, diagrams,
and verification plan. Build several focused, demonstrable slices rather than one mega
change. Never edit another agent's owned source or living docs. Use the programme interface
queue for cross-domain work. Preserve useful prototype behavior while moving it behind v2
contracts.

## Owned scope

- `backend/app/events/**`, `jobs/**`, `actions/**`, `traces/**` and owned models/migrations/tests.
- Postgres event inbox/outbox and leased job runtime, including migration away from Redis/RQ behavior.
- Traces, runs, spans, tool invocations, actions, attempts, evidence, audit, incidents, search and export contracts.
- Frontend `/activity`, trace detail, incident detail, and trace/action state components specific to these routes.

## Explicitly out of scope

- Do not implement Shopify/email provider calls (A04) or CS policy (A05).
- Do not own Hermes transport (A03), financial definitions (A08), global UI primitives (A06), or compose removal of Redis (A09).
- Do not claim complete Hermes coverage for observer-only activity.

## Work packages

1. Audit current activity/audit, queue, webhook worker, retries, connector writes, and any idempotency helpers.
2. Implement common event envelope, durable inbox acceptance/deduplication, transactional outbox, leased jobs, heartbeat/reclaim, concurrency keys, bounded retry/dead letter.
3. Implement trace/run/span/tool-invocation records with honest verified/observed/imported/unknown coverage and W3C-compatible context propagation.
4. Implement generic action intent/digest/idempotency, attempts, state history, `outcome_unknown`, reconciliation port, and exact actor/store/connection binding fields.
5. Implement evidence, administrative audit, incident records, tamper-evident integrity fields where specified, role-filtered search, and agent-readable trace tools.
6. Build Activity/trace/incident surfaces using A06 primitives; show uncertainty, evidence, retries, approvals, and comparison hooks.
7. Provide fakes/contract fixtures so A03–A08 can integrate without direct table access.

## Cross-agent contracts

Expose EventInbox, JobQueue, TraceRecorder, ToolInvocationRecorder, ActionService, ReconciliationPort, EvidenceStore, AuditSink, IncidentService, and search/tool contracts. Consume A01 identity/context and A04 connector-execution port.

## Ready-for-integration acceptance

- [ ] Duplicate events and concurrent intent produce one normalized effect/action.
- [ ] Expired leases recover without starting an unsafe duplicate external attempt.
- [ ] A dispatched timeout can enter `outcome_unknown` and cannot be blindly retried.
- [ ] Seeded traces are searchable by ticket/order/customer/action/tool/date/actor/status.
- [ ] Restricted evidence is filtered server-side and coverage labels are honest.
- [ ] Existing queue behavior has a tested migration/compatibility path before A09 removes Redis.

## Common traps

- Treating logs as the product trace.
- Putting provider-specific logic into the action core.
- Generating an idempotency string without a database uniqueness/state model.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
