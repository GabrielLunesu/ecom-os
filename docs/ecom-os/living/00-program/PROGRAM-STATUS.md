---
owner: A00
baseline_commit: 3909904580732c27a9c6821ef44487c706d6a180
coordination_branch: agent/a00-orchestrator
published_alias: coordination/program
last_verified_against: d8b186b66f75bc9c0420bdae5b81386e156f9e38
---

# Programme Status

Required reading complete for this checkpoint: root `AGENTS.md`; all files in
`docs/ecom-os/specs/`; all files in `docs/ecom-os/parallel-build/`; all programme living
docs; every builder `CURRENT.md` and `INTERFACES.md`; and
`agent-prompts/handoffs/A00-program-auditor.md`.

| Agent | Canonical branch in prompts/docs | Observed local branch | Reported status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|---|
| A00 | `coordination/program` | `agent/a00-orchestrator`; publication alias `coordination/program` | discovery | Programme baseline and audit queue | Branch name mismatch remains in this branch's normative parallel docs; `origin/main` launch cards confirm the observed branch names | Required reading complete; branch/SHA verified; `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` inspected |
| A01 | `agent/A01-platform-foundation` | `agent/a01-foundation` at local commit `4fa6bc0`; no `origin/agent/a01-foundation` ref observed | local discovery | Platform/identity contracts | Local commit is unpublished to `origin`; repo-layout decision request needed; no v2 code/tests yet | Local commit `docs(A01): publish discovery checkpoint...`; `CURRENT.md` and `INTERFACES.md` inspected |
| A02 | `agent/A02-durable-core` | `agent/a02-trace-ledger` at `3909904` | not_started | Durable core | Living docs still placeholders | None |
| A03 | `agent/A03-hermes-integration` | `agent/a03-hermes-runtime` at `3909904`; local uncommitted docs plus Hermes/tool-catalog draft, including A00-owned programme files | local audit_complete + first catalog/bridge draft | Hermes bridge/chat | Unpublished source; OpenClaw-vs-Hermes decision needed; no real Hermes conformance evidence | Local `backend/app/hermes/**`, `backend/app/tools/**`, `test_tool_catalog.py`; targeted test `19 passed` |
| A04 | `agent/A04-commerce-connectors` | `agent/a04-cs` at `3909904`; local uncommitted docs plus connector primitive draft, including A00-owned programme files | local discovery + first binding draft | Connector/read model | Unpublished source; blocked on A01/A02/A03/A06 contracts; no tests observed | Local `backend/app/connectors/{binding,errors}.py`; no targeted test file observed |
| A05 | `agent/A05-customer-service` | `agent/a05-finance` at `3909904`; local uncommitted docs plus source/migration/test draft | local discovery + first invariant draft | CS/autonomy | Unpublished source; blocked on A02/A03/A04/A06 contracts for production writes | Local `ticket_lifecycle.py`, migration `a05c5f1e0001`, and `test_a05_ticket_lifecycle.py` inspected |
| A06 | `agent/A06-design-system` | `agent/a06-ui-system` at `3909904`; local uncommitted docs/design docs plus frontend theme draft | local discovery + first dark-theme draft | UI source of truth | Unpublished source; no tests observed; shape dependencies pending for trace/action/KPI cards | Local `ThemeToggle`, theme hook/script, token/global CSS diffs inspected |
| A07 | `agent/A07-operator-workspace` | `agent/a07-chat` at `3909904`; local uncommitted docs plus API/service/schema/migration/test draft | local discovery + first workspace draft | Today/tasks/knowledge | Unpublished source; migration down-revision is not current baseline head | Local operator workspace API/service/schema/model/migration; targeted test `6 passed` |
| A08 | `agent/A08-finance-brief` | `agent/a08-ops-briefs` at `3909904`; local uncommitted docs plus source/migration/test draft, including A00-owned programme file | local discovery + first formula/model draft | Finance/daily brief | Unpublished source; migration will conflict with other current-head drafts; blocked on A01/A02/A03/A04/A06/A07 contracts | Local metrics formulas/models/migration; targeted tests `7 passed` |
| A09 | `agent/A09-production-integration` | `agent/a09-integration` at local commit `59b43ec` plus uncommitted CI/security draft; no `origin/agent/a09-integration` ref observed | local discovery + first gate draft | Production/integration | Local commit/source is unpublished to `origin`; integration gate remains closed | Local import-boundary script, gitleaks config, CI diff; script selftest/check passed |

## Current programme statement

After `git fetch --all --prune`, the only observed `origin` agent/programme refs are
`origin/agent/a00-orchestrator` and `origin/coordination/program`, both at `d8b186b`.
Local sibling worktrees have advanced unevenly: A01 and A09 have local docs-only commits;
A03/A04/A05/A06/A07/A08/A09 have unpublished worktree diffs; A02 remains placeholder-only.
Because these builder branches are not visible through `origin`, they are current local
evidence for A00 monitoring but not ready-for-integration evidence. The interface registry
remains proposed-only.

A03, A04, A05, A06, A07, A08, and A09 now have local source/config/test drafts. They are
not integration candidates yet. A03 has a canonical tool catalog/HermesBridge skeleton
with targeted catalog tests passing; A04 has exact-binding connector primitives but no
observed test; A05 has a ticket lifecycle invariant draft; A06 has dark-theme/no-FOUC
frontend work without observed tests; A07 has operator workspace API/service/model tests
passing but its migration revises an older migration (`e2f9c6b4a1d3`) instead of the
current baseline head (`a0b1c2d3e4f5`); A08 has deterministic metric formula/model tests
passing and a migration that also revises current baseline head; A09 has import-boundary
and secret-scan CI drafts with the boundary script passing locally. These need owner
commits, exact verification evidence in living docs, accepted dependencies, and A09
migration-head handling before queueing.

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
