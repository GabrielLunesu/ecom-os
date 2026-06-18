# A00 — Program Auditor and Orchestrator Handoff

**Branch:** `coordination/program`

## Mission

Maintain an independent, current view of what all builders are doing, identify architecture and integration failures early, and publish the next safe integration order. You inspect and report; you do not control other agents and you do not implement features.

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

- `docs/ecom-os/living/00-program/**` only.
- Read access to every branch, diff, test result, migration, and living document.
- You may run non-destructive checks and test commands.

## Explicitly out of scope

- Do not edit application source, tests, migrations, dependencies, generated files, agent-owned living docs, or normative specs.
- Do not merge, rewrite, or force-push builder branches.
- Do not mark another agent ready; record evidence and disagreement.
- Do not turn programme docs into dated meeting notes or a changelog.

## Work packages

1. Establish the baseline SHA, branch map, and actual starting health in `PROGRAM-STATUS.md`.
2. Continuously reconcile each branch against source ownership, accepted interfaces, invariants, and Build Spec gates.
3. Maintain only current open dependencies, interface collisions, P0–P3 findings, decision requests, quality-gate evidence, and merge ordering.
4. Inspect whether living docs match code. Flag stale claims, undocumented behavior, duplicate contracts, hidden writes, fake trace coverage, UI forks, migration conflicts, and untested degraded states.
5. For every `ready_for_integration` branch, verify exact test evidence, migrations, rollback/degradation behavior, current docs, and cross-agent compatibility.
6. Publish a concise current programme statement that builders can read through `git show coordination/program:...`.

## Cross-agent contracts

You consume all branch artifacts and expose programme status/findings only. Architecture choices remain with the documented owner and product owner/ADR process.

## Ready-for-integration acceptance

- [ ] Every active branch and blocker is represented accurately.
- [ ] Every open finding has severity, evidence, affected owner, and an objective exit condition.
- [ ] The integration queue respects actual dependencies rather than activity or optimism.
- [ ] Resolved findings are removed after durable tests/docs encode the result.
- [ ] No programme claim says “verified” without inspectable evidence.

## Common traps

- Acting like a manager that assigns work instead of an auditor that exposes state.
- Fixing code yourself, which destroys independent review.
- Keeping historical noise instead of current actionable truth.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
