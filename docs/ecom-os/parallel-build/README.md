# Parallel Build Programme

This directory defines how multiple coding agents build Ecom-OS without producing ten
incompatible implementations.

## Normative order

1. `/AGENTS.md`
2. `../specs/02-TECH-DECISIONS.md`
3. `../specs/ECOM-OS-RUNTIME-SPEC.md` and `../specs/ECOM-OS-BUILD-SPEC.md`
4. the remaining files in `../specs/`
5. this parallel-build protocol
6. living documents

Living documents may describe current implementation state, dependencies, blockers, and
verified behavior. They cannot silently override an invariant, ADR, or accepted spec.
When implementation evidence requires a normative change, open a decision request and
write an ADR after owner approval.

## Core rule

Parallelism is created by **stable ownership and explicit interfaces**, not by allowing
all agents to edit everything. Each builder owns a vertical domain and its tests, routes,
backend modules, and living documents. Shared registries, global UI primitives, deployment
files, lockfiles, and normative documentation have designated owners.

## Files in this directory

- `TEAM-TOPOLOGY.md` — why ten agents and what each owns.
- `OPERATING-PROTOCOL.md` — rules every agent follows.
- `FILE-OWNERSHIP.md` — source and route ownership.
- `BRANCH-AND-INTEGRATION.md` — worktrees, coordination branch, and merge gates.
- `CURRENT-REPO-BASELINE.md` — verified launch-time stack and prototype facts.
- `CURRENT-REPO-MIGRATION-MAP.md` — how to evolve the existing prototype.
- `UI-EXTRACTION-PROTOCOL.md` — how `dashboard-inspo/` becomes the UI source of truth.
- `LAUNCH-CHECKLIST.md` — operator launch sequence.
- `PROMPT-MANIFEST.md` — `/goal` files and verified character counts.
