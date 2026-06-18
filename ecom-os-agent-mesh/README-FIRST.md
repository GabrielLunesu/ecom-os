# Ecom-OS Parallel Build Kit

This kit is the repo-ready operating system for a **10-agent build**:

- **1 program auditor** that changes coordination documentation only;
- **8 domain builders** with non-overlapping vertical ownership;
- **1 production/integration builder** that owns release engineering, full-system quality,
  and controlled integration glue.

Ten is the recommended number. Fewer than ten forces Hermes, traceability, UI foundations,
commerce sync, customer service, finance, and production operations into conflicting mega-
branches. More than ten creates more coordination overhead than useful parallelism at the
current architecture boundary.

## Install

1. Commit the current repository and record the baseline commit SHA.
2. Ensure `dashboard-inspo/` exists in that baseline. It is a required design input, not a
   runtime dependency.
3. Copy everything under `repo-overlay/` into the repository root.
4. Replace the old root `AGENTS.md` with the supplied one. Remove or replace stale duplicate
   architecture/spec files so agents cannot read both v1 and v2 as canonical.
5. Fill `docs/ecom-os/living/00-program/PROGRAM-STATUS.md` with the baseline SHA.
6. Create one branch/worktree per agent using the names in
   `docs/ecom-os/parallel-build/BRANCH-AND-INTEGRATION.md`.
7. Launch A00 first so the coordination branch exists, then launch A01–A09 concurrently.
   All ten may run at once, but they must not share one working tree or branch.
8. Give each agent the matching file from `agent-prompts/goals/` as its `/goal`. The agent
   then reads its full handoff from `agent-prompts/handoffs/`.

## Important

The living documents are **current-state manuals**, not diaries and not changelogs. They
are rewritten as the implementation changes. Historical rationale belongs in ADRs; source
history belongs in Git.

The current application is migration input, not disposable scaffolding. Agents must audit
and preserve useful working behavior, then bring it behind the v2 contracts rather than
restart from a blank repository.
