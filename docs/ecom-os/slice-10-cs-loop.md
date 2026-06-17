# Ecom-OS — Slice 10: CS agent loop (WISMO SOP)

Build Spec §6 (AgentRuntime), §8.10, §9a (acceptance test). Invariants 2, 3, 4.

## What shipped
- `AgentRuntime` interface (swappable; OpenClaw/LLM runtime drops in later).
- `InAppCSRuntime` (v1, deterministic): for new/auto_handling tickets it classifies
  WISMO, looks up the order in Shopify (read-only), cites the vault shipping policy,
  redirects to the tracking page, sends the reply via the inbox, records evidence, and
  auto-closes (resolved). Non-WISMO -> escalate to needs_rep.
- `wismo.py`: pure, injection-safe SOP helpers — customer text is only pattern-matched
  for intent + order ref, never executed as instructions (Invariant 4). No refund tool
  exists on the runtime (Invariant 2). needs_rep/resolved are never re-auto'd (Invariant 3).
- `cs_loop.run_cs_loop`: gated on the §1.5 health check; ingest + handle. API `POST /ecom/cs/run`.

## Verify
- 5 runtime tests (no-refund, WISMO happy path, sticky escalation, injection-safe,
  non-WISMO escalation) pass.
- **Live E2E**: a real "Where is my order #1001?" email -> ingested -> agent looked up
  order #1001 (fulfilled), cited shipping policy + tracking page, sent the reply via
  Outlook, ticket auto-closed (resolved). Other unread mail escalated to needs_rep.
