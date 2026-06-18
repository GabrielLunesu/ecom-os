# Branch, Worktree, and Integration Protocol

## Branches

| Agent | Branch |
|---|---|
| A00 | `coordination/program` |
| A01 | `agent/A01-platform-foundation` |
| A02 | `agent/A02-durable-core` |
| A03 | `agent/A03-hermes-integration` |
| A04 | `agent/A04-commerce-connectors` |
| A05 | `agent/A05-customer-service` |
| A06 | `agent/A06-design-system` |
| A07 | `agent/A07-operator-workspace` |
| A08 | `agent/A08-finance-brief` |
| A09 | `agent/A09-production-integration` |

All branches start from the same recorded baseline commit. `main` is not a shared scratch
branch.

## Worktree example

```bash
BASE=<baseline-sha>
mkdir -p ../ecom-os-worktrees
git branch coordination/program "$BASE"
git worktree add ../ecom-os-worktrees/A00 coordination/program

git branch agent/A01-platform-foundation "$BASE"
git worktree add ../ecom-os-worktrees/A01 agent/A01-platform-foundation
# Repeat using the table for A02–A09.
```

## Coordination without sharing a worktree

A00 commits only `docs/ecom-os/living/00-program/**` on `coordination/program`. Builders
inspect the latest programme state without merging it into unfinished code:

```bash
git fetch --all --prune
git show coordination/program:docs/ecom-os/living/00-program/PROGRAM-STATUS.md
git show coordination/program:docs/ecom-os/living/00-program/REVIEW-FINDINGS.md
```

When using a remote, substitute `origin/coordination/program`. A00 reads each pushed
builder branch in the same way. Builder-owned living docs travel with that builder's code.

## Status lifecycle

`discovery` → `contract_ready` → `implementing` → `verification` →
`ready_for_integration` → `integrated`

Exceptional states: `blocked`, `superseded`, `paused`.

Only the agent owner changes its own status. A00 may report disagreement in
`REVIEW-FINDINGS.md`; it does not falsify another branch's status.

## Recommended integration order

Agents run concurrently, but merges respect contracts:

1. documentation/coordination baseline;
2. A01 common contracts and identity skeleton;
3. A06 tokens, primitives, shell, and UI governance;
4. A09 early CI/boundary enforcement;
5. A02 durable event/trace/action core;
6. A03 Hermes bridge and canonical chat;
7. A04 connector/read model;
8. A05 CS/action/autonomy vertical;
9. A08 finance and daily brief;
10. A07 Today/tasks/knowledge composition;
11. A09 production topology, restore/update, extension baseline, and release gate.

This is merge order, not start order.

## Ready-for-integration gate

A09 may integrate a branch only when:

- its owner marks it `ready_for_integration`;
- owned living docs describe current code;
- required tests and migrations pass with evidence;
- no open P0/P1 A00 finding applies;
- interfaces consumed are accepted/versioned;
- the branch is rebased or merge-tested against the current integration base;
- UI work uses A06 primitives and includes required states;
- external writes meet the action contract.

A09 resolves central registration, generated clients, lockfiles, migration heads, and
compose wiring. It does not silently redesign domain behavior during conflict resolution.
