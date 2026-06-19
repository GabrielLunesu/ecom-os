---
owner: A00
baseline_commit: 3909904580732c27a9c6821ef44487c706d6a180
coordination_branch: agent/a00-orchestrator
published_alias: coordination/program
last_verified_against: 5c5def76c67eb9e3438459b585ab50885bfff840
---

# Programme Status

Required reading complete for this checkpoint: root `AGENTS.md`; all files in
`docs/ecom-os/specs/`; all files in `docs/ecom-os/parallel-build/`; all programme living
docs; every builder `CURRENT.md` and `INTERFACES.md`; and
`agent-prompts/handoffs/A00-program-auditor.md`.

| Agent | Canonical branch in prompts/docs | Observed local branch | Reported status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|---|
| A00 | `coordination/program` | `agent/a00-orchestrator`; publication alias `coordination/program` | discovery | Programme baseline and audit queue | Branch name mismatch remains in this branch's normative parallel docs; `origin/main` launch cards confirm the observed branch names | Required reading complete; branch/SHA verified; `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` inspected |
| A01 | `agent/A01-platform-foundation` | `agent/a01-foundation` at local commit `6658b82`; no `origin/agent/a01-foundation` ref observed | local `ready_for_integration` claim | Platform/identity contracts | Local source is unpublished; repo-layout decision request needed; A08 has a duplicate Money type to reconcile; consumed ports still need acceptance | Local identity foundation/API/enforcement/health/contracts/redaction slices; ruff and mypy pass; full backend suite `628 passed, 1 xfailed`; branch-local Alembic head `a01_0001_identity` |
| A02 | `agent/A02-durable-core` | `agent/a02-trace-ledger` at `3909904`; local uncommitted durable-core service/model/migration/docs draft | local durable-core draft | Durable core | Unpublished source; A02 ports not accepted by consumers yet; integration/E2E wiring still pending | Local `backend/app/{actions,events,jobs,traces}/**`, `models/{actions,events,traces}.py`, migration `a02d1e2f3a4b`; targeted tests `5 passed`; ruff and mypy pass; branch-local Alembic head `a02d1e2f3a4b` |
| A03 | `agent/A03-hermes-integration` | `agent/a03-hermes-runtime` at local commit `ea65611`; no `origin/agent/a03-hermes-runtime` ref observed | local bridge/catalog/invoker/run/channel/conformance commit | Hermes bridge/chat | Unpublished source; OpenClaw-vs-Hermes decision needed; real pinned-Hermes conformance evidence still missing; local owner docs contain stale status/commit text | Local `backend/app/hermes/**`, `backend/app/tools/**`; targeted v2 tests `57 passed` |
| A04 | `agent/A04-commerce-connectors` | `agent/a04-cs` at local commit `46ef05d`; no `origin/agent/a04-cs` ref observed | local connector commit | Connector/read model | Local source is unpublished; blocked on accepted A01/A02/A03/A06 contracts | Local `backend/app/connectors/**`, migration `a04commerce01`; targeted tests `33 passed`; branch-local Alembic head `a04commerce01` |
| A05 | `agent/A05-customer-service` | `agent/a05-finance` at `3909904`; local uncommitted docs plus lifecycle/lease/action-policy/shadow-draft/action-proposal/action-execution source, migrations, and tests | local discovery + invariant/lease/action-policy/shadow-draft/proposal/execution draft | CS/autonomy | Unpublished source; blocked on accepted A02/A03/A04/A06 contracts for production writes | Local CS lifecycle/proposal/execution services, migrations through `a05f9d4e0004`; targeted tests `24 passed`; branch-local Alembic head `a05f9d4e0004` |
| A06 | `agent/A06-design-system` | `agent/a06-ui-system` at `3909904`; local uncommitted docs/design docs plus frontend theme/mobile/state/component-lab/action/entity/evidence/accessibility draft, including A00-owned programme file | local discovery + UI primitive/component/card/a11y draft | UI source of truth | Unpublished source; whole-project frontend eslint fails in A07-owned `brand/page.tsx`; A06/A08 both have A00-owned programme-file edits | Local frontend typecheck passed; full Vitest `150 passed`; axe a11y subset `10 passed`; `npx eslint .` fails 2 errors in `brand/page.tsx` |
| A07 | `agent/A07-operator-workspace` | `agent/a07-chat` at `3909904`; local uncommitted docs plus API/service/schema/migration/test/frontend workspace draft | local discovery + workspace/knowledge draft | Today/tasks/knowledge | Unpublished source; migration down-revision is not current baseline head | Local operator workspace API/service/schema/model/migration and frontend API/test; backend targeted tests `6 passed`; frontend Vitest `2 passed` |
| A08 | `agent/A08-finance-brief` | `agent/a08-ops-briefs` at `3909904`; local uncommitted docs plus source/migration/test/API/tool/daily-brief-tool draft, including A00-owned programme file | local discovery + formula/model/service/API/tool/brief draft | Finance/daily brief | Unpublished source; migration will conflict with other branch-local heads; duplicate Money type vs A01; blocked on A01/A02/A03/A04/A06/A07 contracts | Local metrics formulas/models/read models/snapshot service/API/legacy source/tools/daily briefs/migration; targeted tests `27 passed`; branch-local Alembic head `a08_001_metric_snapshots` |
| A09 | `agent/A09-production-integration` | `agent/a09-integration` at local commit `6d8b1e3`; no `origin/agent/a09-integration` ref observed | local CI/health/maintenance/backup/restore/release/extensions/E2E commit + runbook docs | Production/integration | Local source is unpublished; integration gate remains closed; live Docker/Postgres N-1 restore drill and domain-branch wiring remain pending; owner docs still contain stale builder-baseline gate text | Commits through `docs(A09): operator runbooks...`; expanded operations tests `54 passed`; import-boundary check passed; branch-local Alembic head `a09c1d2e3f40` |

## Current programme statement

The pre-checkpoint `git fetch --all --prune` saw only `origin` agent/programme refs
`origin/agent/a00-orchestrator` and `origin/coordination/program`, both then at `5c5def7`;
this checkpoint publishes the refreshed A00 docs to those same refs.
Local sibling worktrees have advanced unevenly: A01, A03, A04, and A09 have local commits;
A02/A05/A06/A07/A08 have unpublished worktree diffs.
Because these builder branches are not visible through `origin`, they are current local
evidence for A00 monitoring but not ready-for-integration evidence. The interface registry
remains proposed-only.

A01, A02, A03, A04, A05, A06, A07, A08, and A09 now have local source/config/test drafts.
They are not integration candidates yet. A01 has shared UUIDv7/Money/time/error/request
context, identity-table, identity API, service/channel enforcement, health, contract, and
redaction evidence with full backend tests passing; A02 has durable inbox/job/trace/action
services, a migration, owner docs, and focused checks passing; A03 has HermesBridge/tool
catalog/invoker plus background-run/channel/conformance fixtures passing, but still no real
pinned-Hermes conformance; A04 has a local committed connector slice with targeted tests
passing; A05 has ticket lifecycle, CS-loop lease, action-policy, WISMO shadow-draft,
action-proposal, and local attempt-execution tests passing; A06 has theme/mobile-nav,
component-lab, operational-state, action/entity/evidence cards, and a11y tests passing,
but whole-project frontend lint fails in A07-owned brand UI; A07 has operator workspace backend and frontend tests passing but its
migration revises an older migration (`e2f9c6b4a1d3`) instead of the current baseline head
(`a0b1c2d3e4f5`); A08 has deterministic metric formula/model/read-model/service/API,
legacy-source, read-tool, daily-brief, and daily-brief-tool tests passing, a migration that
revises current baseline head, and a duplicate Money type relative to A01; A09 has local
CI/security, System health, maintenance, backup/restore, release/update, extensions, and
operational E2E evidence passing. These need owner pushes, exact verification evidence in
living docs, accepted dependencies, and A09 migration-head handling before queueing.

A06 and A08 worktrees currently contain local edits to A00-owned files under
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
