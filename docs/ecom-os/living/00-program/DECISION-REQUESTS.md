# Open Decision Requests

Use this only when work cannot be resolved by an existing invariant, ADR, spec, or owned
interface. A00 records the conflict; the product owner accepts/rejects; the relevant owner
writes an ADR if the decision is architectural.

| ID | Raised by | Decision needed | Options and consequences | Work that can continue | Owner decision |
|---|---|---|---|---|---|
| DR-001 | A00 | Which branch map is authoritative for the active parallel programme? | Option A: create/use the canonical branches in `docs/ecom-os/parallel-build/BRANCH-AND-INTEGRATION.md` and update current worktrees accordingly. Option B: accept the observed launch override branches (`agent/a00-orchestrator`, `agent/a01-foundation`, `agent/a02-trace-ledger`, `agent/a03-hermes-runtime`, `agent/a04-cs`, `agent/a05-finance`, `agent/a06-ui-system`, `agent/a07-chat`, `agent/a08-ops-briefs`, `agent/a09-integration`) and record the mapping in programme docs/prompts. `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` and `AGENT-LAUNCH-CARDS.md` are evidence that Option B was used operationally, but this branch's normative protocol still says Option A. Without one authoritative map, A00/A09 branch inspection and ready-for-integration gates are ambiguous. | Builders can audit code, update owned living docs, and build typed local ports in their current worktrees; A00 will continue reporting against the observed branches and the explicit launch instruction until superseded. | Open |
