# Launch Checklist

## Baseline

- [ ] Current work committed; baseline SHA recorded.
- [ ] `main` builds and its known failures are documented.
- [ ] v2 specs copied to `docs/ecom-os/specs/`.
- [ ] root `AGENTS.md` replaced with the v2 + parallel rules version.
- [ ] stale duplicate specs removed or replaced with pointers.
- [ ] `dashboard-inspo/` exists and is committed/readable by A06.
- [ ] no production secrets are present in the repository or agent prompts.

## Workspaces

- [ ] `coordination/program` branch/worktree created for A00.
- [ ] A01–A09 branches/worktrees created from the same SHA.
- [ ] each agent has write access only to its worktree/branch.
- [ ] branch names match `BRANCH-AND-INTEGRATION.md`.

## Launch

- [ ] Launch A00 with `A00-program-auditor.goal.md`.
- [ ] Launch A01–A09 with their matching `/goal` files.
- [ ] Confirm each agent read its handoff and set its living status to `discovery`.
- [ ] Confirm each builder publishes an inventory/interface plan before large edits.
- [ ] Confirm A06 treats multi-tenant visuals as store/context switching only.
- [ ] Confirm A05 uses v2 owner sovereignty, not the old permanent no-refund model.

## First programme gate

Before integrating customer-facing automation:

- [ ] A01 common identity/contracts exist.
- [ ] A02 durable trace/action/job primitives pass tests.
- [ ] A03 Hermes capability probe and one traced read tool pass.
- [ ] A04 exact connector binding and reconciliation fixture pass.
- [ ] A06 shell/tokens/primitives are usable by route owners.
- [ ] A09 CI runs boundary, migration, and conformance checks.
- [ ] A00 reports no unresolved P0/P1 architectural finding.
