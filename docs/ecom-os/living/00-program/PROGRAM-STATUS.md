---
owner: A00
baseline_commit: 3909904580732c27a9c6821ef44487c706d6a180
coordination_branch: agent/a00-orchestrator
published_alias: coordination/program
last_verified_against: a481be9590549362ab24019a5c2a22464a84a205
---

# Programme Status

Required reading complete for this checkpoint: root `AGENTS.md`; all files in
`docs/ecom-os/specs/`; all files in `docs/ecom-os/parallel-build/`; all programme living
docs; every builder `CURRENT.md` and `INTERFACES.md`; and
`agent-prompts/handoffs/A00-program-auditor.md`.

| Agent | Canonical branch in prompts/docs | Observed local branch | Reported status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|---|
| A00 | `coordination/program` | `agent/a00-orchestrator`; publication alias `coordination/program` | discovery | Programme baseline and audit queue | Branch name mismatch remains in this branch's normative parallel docs; `origin/main` launch cards confirm the observed branch names | Required reading complete; branch/SHA verified; `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` inspected |
| A01 | `agent/A01-platform-foundation` | `agent/a01-foundation` at local commit `4fa6bc0` plus uncommitted core type/error draft; no `origin/agent/a01-foundation` ref observed | local discovery + first shared-type draft | Platform/identity contracts | Local source is unpublished; repo-layout decision request needed; A08 has a duplicate Money type to reconcile | Local `core/{errors,ids,money,time}.py`; targeted test `23 passed` |
| A02 | `agent/A02-durable-core` | `agent/a02-trace-ledger` at `3909904` | not_started | Durable core | Living docs still placeholders | None |
| A03 | `agent/A03-hermes-integration` | `agent/a03-hermes-runtime` at `3909904`; local uncommitted docs plus Hermes/tool-catalog draft, including A00-owned programme files | local audit_complete + bridge/catalog fixture draft | Hermes bridge/chat | Unpublished source; OpenClaw-vs-Hermes decision needed; no real Hermes conformance evidence | Local `backend/app/hermes/**`, `backend/app/tools/**`; targeted tests `33 passed` |
| A04 | `agent/A04-commerce-connectors` | `agent/a04-cs` at `3909904`; local uncommitted docs plus connector primitive draft, including A00-owned programme files | local discovery + first binding/registry draft | Connector/read model | Unpublished source; blocked on A01/A02/A03/A06 contracts | Local `backend/app/connectors/**`; targeted test `15 passed` |
| A05 | `agent/A05-customer-service` | `agent/a05-finance` at `3909904`; local uncommitted docs plus lifecycle/lease source, migration, and tests | local discovery + first invariant/lease draft | CS/autonomy | Unpublished source; blocked on A02/A03/A04/A06 contracts for production writes | Local `ticket_lifecycle.py`, CS loop lease diff, migration `a05c5f1e0001`; targeted tests `6 passed` |
| A06 | `agent/A06-design-system` | `agent/a06-ui-system` at `3909904`; local uncommitted docs/design docs plus frontend theme/mobile/state draft | local discovery + first UI primitive draft | UI source of truth | Unpublished source; frontend lint was stopped after no output beyond startup, so static check is inconclusive | Local theme/mobile nav/sheet/empty/error/forbidden/freshness/skeleton files inspected |
| A07 | `agent/A07-operator-workspace` | `agent/a07-chat` at `3909904`; local uncommitted docs plus API/service/schema/migration/test draft | local discovery + first workspace draft | Today/tasks/knowledge | Unpublished source; migration down-revision is not current baseline head | Local operator workspace API/service/schema/model/migration; targeted test `6 passed` |
| A08 | `agent/A08-finance-brief` | `agent/a08-ops-briefs` at `3909904`; local uncommitted docs plus source/migration/test draft, including A00-owned programme file | local discovery + formula/model/service draft | Finance/daily brief | Unpublished source; migration will conflict with other current-head drafts; duplicate Money type vs A01; blocked on A01/A02/A03/A04/A06/A07 contracts | Local metrics formulas/models/snapshot service/migration; targeted tests `9 passed` |
| A09 | `agent/A09-production-integration` | `agent/a09-integration` at local commit `1e71b0d` plus uncommitted system-health draft; no `origin/agent/a09-integration` ref observed | local CI gate commit + first system-health draft | Production/integration | Local commit/source is unpublished to `origin`; integration gate remains closed | Commit `ci(A09): add import-boundary...`; local `/system/health` draft; targeted tests `14 passed`; import-boundary check passed |

## Current programme statement

After `git fetch --all --prune`, the only observed `origin` agent/programme refs are
`origin/agent/a00-orchestrator` and `origin/coordination/program`, both at `a481be9`.
Local sibling worktrees have advanced unevenly: A01 and A09 have local docs-only commits;
A03/A04/A05/A06/A07/A08/A09 have unpublished worktree diffs; A02 remains placeholder-only.
Because these builder branches are not visible through `origin`, they are current local
evidence for A00 monitoring but not ready-for-integration evidence. The interface registry
remains proposed-only.

A01, A03, A04, A05, A06, A07, A08, and A09 now have local source/config/test drafts. They
are not integration candidates yet. A01 has shared UUIDv7/Money/time/error drafts with
targeted tests passing; A03 has a canonical tool catalog/HermesBridge fixture skeleton
with targeted catalog/bridge tests passing; A04 has exact-binding connector primitives
with targeted tests passing; A05 has ticket lifecycle and CS-loop lease tests passing;
A06 has dark-theme/mobile-nav/operational-state UI work but its frontend lint check was
stopped as inconclusive; A07 has operator workspace API/service/model tests passing but
its migration revises an older migration (`e2f9c6b4a1d3`) instead of the current baseline
head (`a0b1c2d3e4f5`); A08 has deterministic metric formula/model/service tests passing,
a migration that also revises current baseline head, and a duplicate Money type relative
to A01; A09 has a published local CI/security commit plus an uncommitted System health
draft with targeted tests passing. These need owner commits, exact verification evidence
in living docs, accepted dependencies, and A09 migration-head handling before queueing.

A03, A04, and A08 worktrees currently contain local edits to A00-owned files under
`docs/ecom-os/living/00-program/**`. A00 will not copy those files blindly; any useful
requests are reconciled into this branch by A00 only.

The immediate integration boundary is documentation/coordination only. Do not integrate
feature work until each builder updates its owned living docs with concrete code paths,
interfaces, verification evidence, and branch identity.

A00 remains checked out on `agent/a00-orchestrator` per launch instruction. The
`coordination/program` ref is maintained as a read-only publication alias for builders
that follow the canonical `git show coordination/program:...` lookup documented in the
parallel-build protocol.

Current baseline implementation remains a prototype migration input, not v2-compliant
foundation: it still contains `AgentRuntime`, `/delegate` Hermes gateway assumptions,
direct CS connector sends/discount creation, non-durable realtime email webhook handling,
first-store/first-active-inbox selection, Redis/RQ dependencies, and legacy
OpenClaw/Mission Control modules. These are now recorded as findings to keep them out of
the integration queue until the owning agents migrate or explicitly fence them.

Two old feature branches are present but are not integration candidates:
`feat/ecom-os-slice-1-design-system` and `feat/ecom-os-slice-2-connections` both delete
the v2 agent prompts, programme living docs, and many normative/design docs relative to
`3909904`. They must not be merged as-is into the active parallel programme.
