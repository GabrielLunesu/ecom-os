---
owner: A00
baseline_commit: 3909904580732c27a9c6821ef44487c706d6a180
coordination_branch: agent/a00-orchestrator
published_alias: coordination/program
last_verified_against: 0f7d96466f50762a01d2b254f4a9d7012b1b7751
---

# Programme Status

Required reading complete for this checkpoint: root `AGENTS.md`; all files in
`docs/ecom-os/specs/`; all files in `docs/ecom-os/parallel-build/`; all programme living
docs; every builder `CURRENT.md` and `INTERFACES.md`; and
`agent-prompts/handoffs/A00-program-auditor.md`.

| Agent | Canonical branch in prompts/docs | Observed local branch | Reported status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|---|
| A00 | `coordination/program` | `agent/a00-orchestrator`; publication alias `coordination/program` | discovery | Programme baseline and audit queue | Branch name mismatch remains in this branch's normative parallel docs; `origin/main` launch cards confirm the observed branch names | Required reading complete; branch/SHA verified; `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` inspected |
| A01 | `agent/A01-platform-foundation` | `agent/a01-foundation` at local commit `2be8605` plus uncommitted identity model/migration draft; no `origin/agent/a01-foundation` ref observed | local discovery + shared-type/request-context/identity draft | Platform/identity contracts | Local source is unpublished; repo-layout decision request needed; A08 has a duplicate Money type to reconcile | Local `core/{errors,ids,money,time,context}.py`, `auth/context.py`, `models/identity.py`, migration `a01_0001_identity`; targeted tests `40 passed`; branch-local Alembic head `a01_0001_identity` |
| A02 | `agent/A02-durable-core` | `agent/a02-trace-ledger` at `3909904` | not_started | Durable core | Living docs still placeholders | None |
| A03 | `agent/A03-hermes-integration` | `agent/a03-hermes-runtime` at `3909904`; local uncommitted docs plus Hermes/tool-catalog draft, including A00-owned programme files | local audit_complete + bridge/catalog fixture draft | Hermes bridge/chat | Unpublished source; OpenClaw-vs-Hermes decision needed; no real Hermes conformance evidence | Local `backend/app/hermes/**`, `backend/app/tools/**`; targeted tests `33 passed` |
| A04 | `agent/A04-commerce-connectors` | `agent/a04-cs` at `3909904`; local uncommitted docs plus connector primitive/API/action draft, including A00-owned programme files | local discovery + binding/read-model/webhook/action/API draft | Connector/read model | Unpublished source; blocked on A01/A02/A03/A06 contracts | Local `backend/app/connectors/**`, migration `a04commerce01`; targeted tests `33 passed`; branch-local Alembic head `a04commerce01` |
| A05 | `agent/A05-customer-service` | `agent/a05-finance` at `3909904`; local uncommitted docs plus lifecycle/lease/action-policy/shadow-draft source, migrations, and tests | local discovery + invariant/lease/action-policy/shadow-draft draft | CS/autonomy | Unpublished source; blocked on A02/A03/A04/A06 contracts for production writes | Local `ticket_lifecycle.py`, `cs_action_policy.py`, `cs_shadow_drafts.py`, CS loop lease diff, migrations `a05c5f1e0001`/`a05d7a2b0002`/`a05e8b3c0003`; targeted tests `16 passed`; branch-local Alembic head `a05e8b3c0003` |
| A06 | `agent/A06-design-system` | `agent/a06-ui-system` at `3909904`; local uncommitted docs/design docs plus frontend theme/mobile/state/component-lab draft | local discovery + UI primitive/component-lab draft | UI source of truth | Unpublished source; frontend lint was stopped after no output beyond startup, so static check is inconclusive | Local theme/mobile nav/sheet/empty/error/forbidden/freshness/skeleton/component-lab files inspected; targeted Vitest `20 passed` |
| A07 | `agent/A07-operator-workspace` | `agent/a07-chat` at `3909904`; local uncommitted docs plus API/service/schema/migration/test/frontend workspace draft | local discovery + workspace/knowledge draft | Today/tasks/knowledge | Unpublished source; migration down-revision is not current baseline head | Local operator workspace API/service/schema/model/migration and frontend API/test; backend targeted tests `6 passed`; frontend Vitest `2 passed` |
| A08 | `agent/A08-finance-brief` | `agent/a08-ops-briefs` at `3909904`; local uncommitted docs plus source/migration/test/API/tool draft, including A00-owned programme file | local discovery + formula/model/service/API/tool draft | Finance/daily brief | Unpublished source; migration will conflict with other branch-local heads; duplicate Money type vs A01; blocked on A01/A02/A03/A04/A06/A07 contracts | Local metrics formulas/models/read models/snapshot service/API/legacy source/tools/migration; targeted tests `20 passed` with one aiosqlite thread warning; branch-local Alembic head `a08_001_metric_snapshots` |
| A09 | `agent/A09-production-integration` | `agent/a09-integration` at local commit `42aa648`; no `origin/agent/a09-integration` ref observed | local CI gate + system-health + maintenance-mode commits | Production/integration | Local commits/source are unpublished to `origin`; integration gate remains closed; maintenance pause is not yet proven enforced by A02/A04/A05 write paths | Commits through `feat(A09): maintenance mode / external-write pause primitive`; targeted tests `19 passed` with deprecation warnings; import-boundary check passed; branch-local Alembic head `a09c1d2e3f40` |

## Current programme statement

The pre-checkpoint `git fetch --all --prune` saw only `origin` agent/programme refs
`origin/agent/a00-orchestrator` and `origin/coordination/program`, both then at `0f7d964`;
this checkpoint publishes the refreshed A00 docs to those same refs.
Local sibling worktrees have advanced unevenly: A01 and A09 have local commits; A01 plus
A03/A04/A05/A06/A07/A08 have unpublished worktree diffs; A02 remains placeholder-only.
Because these builder branches are not visible through `origin`, they are current local
evidence for A00 monitoring but not ready-for-integration evidence. The interface registry
remains proposed-only.

A01, A03, A04, A05, A06, A07, A08, and A09 now have local source/config/test drafts. They
are not integration candidates yet. A01 has shared UUIDv7/Money/time/error/request-context
and identity-table drafts with targeted tests passing; A03 has a canonical tool
catalog/HermesBridge fixture skeleton with targeted catalog/bridge tests passing; A04 has
exact-binding connector, read-model, webhook-inbox, action reconciliation, read-tool, and
API primitives with targeted tests passing; A05 has ticket lifecycle, CS-loop lease,
action-policy, and WISMO shadow-draft tests passing; A06 has dark-theme/mobile-nav,
component-lab, and operational-state UI tests passing but its frontend lint check remains
inconclusive; A07 has operator workspace backend and frontend tests passing but its
migration revises an older migration (`e2f9c6b4a1d3`) instead of the current baseline head
(`a0b1c2d3e4f5`); A08 has deterministic metric formula/model/read-model/service/API,
legacy-source, and read-tool tests passing with one aiosqlite thread warning, a migration
that revises current baseline head, and a duplicate Money type relative to A01; A09 has
local CI/security, dimensional System health, and maintenance-mode commits with targeted
tests passing. These need owner pushes, exact verification evidence in living docs,
accepted dependencies, and A09 migration-head handling before queueing.

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
