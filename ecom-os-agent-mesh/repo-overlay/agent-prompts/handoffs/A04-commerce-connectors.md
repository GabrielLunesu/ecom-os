# A04 — Commerce Connectors and Operational Read Models Handoff

**Branch:** `agent/A04-commerce-connectors`

## Mission

Create provider-independent connector contracts, exact account/store binding, safe ingestion, normalized commerce truth, freshness/evidence, and read-oriented Orders/Customers experiences.

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

- Connection records/health and connector adapter interfaces/implementations.
- Signed webhook ingress, provider-event deduplication, initial/incremental sync, source timestamps and freshness.
- Stores, orders, customers, products, fulfilment/tracking/provider references and owned migrations.
- Orders/Customers pages, connection settings, and read tools.

## Explicitly out of scope

- Do not choose CS policy or ticket state (A05).
- Do not bypass A02 for external writes or implement a second action ledger.
- Do not assume Composio is the domain ontology; it is one adapter.
- Do not use “default/latest connected account” for a write.

## Work packages

1. Audit current Composio/direct Shopify/inbox code, connection records, secrets, sync paths, webhooks, data models, and real fixtures.
2. Define stable connector ports with exact brand/store/connection/account binding, read/write classification, provider IDs, typed errors, idempotency support, reconciliation strategy, and redacted diagnostics.
3. Implement raw-body signature verification and durable A02 inbox insertion before parsing/processing.
4. Normalize stores/orders/customers/products/fulfilments/tracking and source/freshness/coverage; retain opaque upstream IDs separately.
5. Implement connection health/startup probes, last-good behavior, wrong-account rejection, rate limits/backoff, and timeout/reconciliation fixtures.
6. Expose evidence-backed read tools and build Orders/Customers/connection-settings routes with stale/partial/degraded states.
7. Emit normalized inbox/message events for A05 without deciding workflow behavior.

## Cross-agent contracts

Consume A01 identity/scope, A02 inbox/jobs/traces/action connector-attempt port, A06 UI. Expose ConnectorRegistry, ConnectionBinding, CommerceReadRepository, ProviderExecutionPort, ReconciliationAdapter, sync events, and read-tool definitions.

## Ready-for-integration acceptance

- [ ] A real/sandbox order can be retrieved by ID and customer with source/freshness/evidence.
- [ ] Duplicate webhook/provider events change normalized state once.
- [ ] Wrong connection/store/account fixtures fail closed with a traced reason.
- [ ] Outage returns last-good data marked stale/partial rather than fabricated current data.
- [ ] Ambiguous provider outcome can be queried/reconciled through the A02 contract.
- [ ] No raw managed OAuth token is stored as ordinary application data.

## Common traps

- Letting connector payloads leak directly into domain/API contracts.
- Mixing synchronization freshness with action success.
- Adding direct provider writes in API routes for convenience.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
