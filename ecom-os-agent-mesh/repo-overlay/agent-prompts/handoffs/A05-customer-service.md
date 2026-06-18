# A05 — Customer Service, Approvals, and Autonomy Handoff

**Branch:** `agent/A05-customer-service`

## Mission

Turn the existing CS/flow-builder work into a production workflow that remains owner-configurable and unrestricted when chosen, while every supported action stays attributable and technically sound.

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

- Tickets/messages/threading/state history, classification, assignment, drafts/proposals, sticky escalation, shadow evaluation.
- CS workflow definitions/prompts owned by Ecom-OS and migration of the existing flow builder.
- Reply/discount/refund or other CS tool definitions selected for v1, grants, policies, approval bindings, emergency pause, mode resolution.
- Customer Service, ticket detail, Approvals, and autonomy-settings routes.

## Explicitly out of scope

- Do not revive the old permanent “CS can never refund” invariant; v2 grants may allow broad tools, including unrestricted mode, when explicitly configured.
- Do not bypass A02 action/attempt/trace records or A04 exact connection binding.
- Do not let customer text grant capability, alter policy, approve action, or write authoritative configuration.
- Do not implement Hermes transport directly.

## Work packages

1. Audit current tickets, flows/prompts, WISMO/refund behavior, LLM generation, live polling, sends, discounts, approvals, and tests. Classify each path as retain, migrate, or remove.
2. Implement idempotent message threading, ticket state/history, one-active-workflow concurrency, assignment, explicit reopen behavior, and sticky human ownership.
3. Implement WISMO classification/background run context through A03, evidence-grounded drafts, prompt/config hashes, shadow mode, and quality reporting.
4. Define CS tool/action schemas and use A02 for exact intent/digest/attempt/reconciliation. Editing an approved body or target creates a new digest/action.
5. Implement grants for disabled/observe/approve/policy/unrestricted; unrestricted removes business caps/approval only, never identity/schema/idempotency/trace/reconciliation.
6. Build queue/detail/approval/autonomy UI with actual action states, evidence, trace links, degraded/unknown states, and emergency pause.
7. Migrate useful visual flows/prompts so configuration affects proposed behavior without becoming an untraced direct execution engine.

## Cross-agent contracts

Consume A01 actor/scope, A02 jobs/traces/actions/approvals support, A03 BackgroundRunPort/tools, A04 ticket-source/commerce/connector ports, A06 UI. Expose ticket/read/action tools and attention events to A07.

## Ready-for-integration acceptance

- [ ] Duplicate/out-of-order messages thread correctly and create one active workflow.
- [ ] Customer prompt injection cannot change grants/config/account/approval or bypass action execution.
- [ ] `needs_rep`/human-owned replies append and notify without silent autonomous restart.
- [ ] Observe mode cannot send; approved edits invalidate approval; timeout-after-acceptance does not duplicate.
- [ ] Unrestricted mode truly bypasses Ecom-OS business caps/approval for the granted scope while technical integrity remains.
- [ ] Every draft and final action links run, evidence, config/prompt version, grant resolution, action, attempt, outcome, and trace.

## Common traps

- Keeping old safety assumptions after the owner-sovereignty ADR changed them.
- Equating LLM text with provider success.
- Letting the flow editor own connector execution instead of producing typed intents.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
