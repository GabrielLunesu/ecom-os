---
owner: A00
baseline_commit: 3909904580732c27a9c6821ef44487c706d6a180
coordination_branch: agent/a00-orchestrator
published_alias: coordination/program
last_verified_against: 2ef30de792b994e54ec8efbbd0405965eaddccd5
---

# Programme Status

Required reading complete for this checkpoint: root `AGENTS.md`; all files in
`docs/ecom-os/specs/`; all files in `docs/ecom-os/parallel-build/`; all programme living
docs; every builder `CURRENT.md` and `INTERFACES.md`; and
`agent-prompts/handoffs/A00-program-auditor.md`.

| Agent | Canonical branch in prompts/docs | Observed local branch | Reported status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|---|
| A00 | `coordination/program` | `agent/a00-orchestrator`; publication alias `coordination/program` | discovery | Programme baseline and audit queue | Branch name mismatch remains in this branch's normative parallel docs; `origin/main` launch cards confirm the observed branch names | Required reading complete; branch/SHA verified; `origin/main:docs/ecom-os/parallel-build/WORKTREE-SETUP-REPORT.md` inspected |
| A01 | `agent/A01-platform-foundation` | `agent/a01-foundation` at local commit `64ca874`; no `origin/agent/a01-foundation` ref observed | local `ready_for_integration` claim, now stale after style commit | Platform/identity contracts | Local source is unpublished; owner docs still say latest verified commit `f92adbb`; full backend pytest could not start in A00 environment because the data volume is at 100% capacity and pytest could not create temp files; repo-layout decision request needed; A08 has a duplicate Money type to reconcile; consumed ports still need acceptance | Local identity foundation/API/enforcement/health/contracts/redaction slices; A00 reran ruff and mypy at `64ca874` and both pass; previous owner evidence at `f92adbb` says full backend suite `628 passed, 1 xfailed`; branch-local Alembic head `a01_0001_identity` |
| A02 | `agent/A02-durable-core` | `agent/a02-trace-ledger` at `3909904`; local uncommitted durable-core service/model/migration/docs plus realtime-webhook, board-webhook dispatch, Activity endpoint, queue-worker rollout, migration-verifier draft, and broad legacy service/connectors/test edits | local durable-core + webhook acceptance/dispatch + trace/action Activity + queue migration draft, with broad cross-module instrumentation/formatting | Durable core | Unpublished source; A02 ports not accepted by consumers yet; integration/E2E wiring still pending; realtime email still uses shared-secret compatibility auth rather than provider-specific raw-body signature verification; broad edits touch non-A02-owned service/connector/CS paths and need owner/interface acceptance before integration | Local `backend/app/{actions,events,jobs,traces}/**`, `api/{ecom_webhooks,board_webhooks,activity}.py`, `services/{queue_worker,webhooks/dispatch}.py`, models, migration verifier, and migration `a02d1e2f3a4b`; A00 reran focused tests `47 passed`; focused ruff and mypy pass; branch-local Alembic head `a02d1e2f3a4b` |
| A03 | `agent/A03-hermes-integration` | `agent/a03-hermes-runtime` at pushed `origin/agent/a03-hermes-runtime` commit `4108248`, with additional local uncommitted post-push edits | pushed bridge/catalog/invoker/run/channel/native/compat/chat-gateway/conformance-gate + HTTP/SSE route + compatibility-matrix/drift-guard branch; newer local edits not published/audited | Hermes bridge/chat | Pushed checkpoint exists, but central router registration remains pending; branch history includes A00-owned programme-file edits; real pinned-Hermes conformance evidence is still missing; OpenClaw is explicitly compat/dev only; conformance gate is intentionally RED until a real Hermes endpoint is supplied; owner docs contain stale frontmatter/status text; local post-push edits are not consumable through `origin` | Pushed `origin/agent/a03-hermes-runtime`; A00 reran focused v2/native/compat/chat-gateway/API/catalog/conformance-gate suite `97 passed` plus manifest drift guard `3 passed`; ruff pass; mypy pass; conformance CLI exits `2` BLOCKED without real Hermes |
| A04 | `agent/A04-commerce-connectors` | `agent/a04-cs` at local commit `46ef05d`; no `origin/agent/a04-cs` ref observed | local connector commit plus staged programme-file collision | Connector/read model | Local source is unpublished; blocked on accepted A01/A02/A03/A06 contracts; worktree has staged A00-owned programme-file edits that would overwrite central status/request queues | Local `backend/app/connectors/**`, migration `a04commerce01`; targeted tests `33 passed`; branch-local Alembic head `a04commerce01`; A04 `INTERFACES.md` now says A04 must not edit `00-program/**`, but staged A00-file edits remain |
| A05 | `agent/A05-customer-service` | `agent/a05-finance` at `3909904`; local uncommitted docs plus lifecycle/lease/action-policy/shadow-draft/action-proposal/action-execution/approval/autonomy/handoff/state-surface/state-API/attention/quality source, migrations, and tests | local discovery + invariant/lease/action-policy/shadow-draft/proposal/execution/approval/autonomy/handoff/state-surface/state-API/attention/quality draft | CS/autonomy | Unpublished source; focused mypy still fails in `cs_state_surface.py`, `cs_quality_report.py`, and `cs_attention_events.py`; blocked on accepted A02/A03/A04/A06 contracts for production writes; migration upgrade/downgrade against a real test database still pending | Local CS lifecycle/proposal/execution/approval/autonomy/handoff/state-surface/API/attention/quality services, migrations through `a05i2f7c0007`; targeted regression suite `99 passed` with async SQLite warnings; focused ruff pass; focused mypy fails; branch-local Alembic head `a05i2f7c0007` |
| A06 | `agent/A06-design-system` | `agent/a06-ui-system` at local commit `a9d870a`; no `origin/agent/a06-ui-system` ref observed | local design-system foundation commit | UI source of truth | Local source is unpublished; commit includes an A00-owned programme file; owner docs still say commit pending/baseline verified; whole-project frontend eslint still fails in A07-owned `brand/page.tsx` | Local frontend typecheck passed; full Vitest `150 passed`; axe a11y subset `10 passed`; A06-owned eslint passed; branch-local commit touches `docs/ecom-os/living/00-program/INTERFACE-REQUESTS.md` |
| A07 | `agent/A07-operator-workspace` | `agent/a07-chat` at `3909904`; local uncommitted docs plus API/service/schema/migration/test/frontend workspace draft | local discovery + workspace/knowledge draft | Today/tasks/knowledge | Unpublished source; migration down-revision is not current baseline head | Local operator workspace API/service/schema/model/migration and frontend API/test; backend targeted tests `6 passed`; frontend Vitest `2 passed` |
| A08 | `agent/A08-finance-brief` | `agent/a08-ops-briefs` at `3909904`; local uncommitted docs plus source/migration/test/API/tool/daily-brief generation/delivery-packet and local `/finance` UI draft, including A00-owned programme file | local discovery + formula/model/service/API/tool/brief/generation/delivery-packet/finance-UI draft | Finance/daily brief | Unpublished source; migration will conflict with other branch-local heads; duplicate Money type vs A01; backend router mount and nav/tool registration remain unaccepted; blocked on A01/A02/A03/A04/A06/A07 contracts | Local metrics formulas/models/read models/snapshot service/API/legacy source/tools/daily briefs/generation/delivery-packet/migration and read-only Finance routes; backend regression `57 passed`; backend ruff/mypy pass; frontend typecheck/eslint pass; Finance route Vitest `8 passed`; branch-local Alembic head `a08_001_metric_snapshots` |
| A09 | `agent/A09-production-integration` | `agent/a09-integration` at local commit `272e65c`; no `origin/agent/a09-integration` ref observed | local CI/health/maintenance/backup/restore/release/extensions/E2E + branch-readiness/migration-head tooling commit | Production/integration | Local source is unpublished; new `scripts/ci/branch_readiness.py` fails ruff/mypy; integration gate remains closed; live Docker/Postgres N-1 restore drill and domain-branch wiring remain pending; owner docs still name older latest verified commit | Local branch-readiness tool reports every builder NOT READY; migration graph and migration-head scripts pass with required env; operations tests `54 passed`; branch-readiness ruff/mypy fail; branch-local Alembic head `a09c1d2e3f40` |

## Current programme statement

The pre-checkpoint `git fetch --all --prune` saw `origin` agent/programme refs
`origin/agent/a00-orchestrator` and `origin/coordination/program`, both then at `2ef30de`,
and new builder ref `origin/agent/a03-hermes-runtime` at `4108248`; this checkpoint
publishes the refreshed A00 docs to the A00 refs only.
Local sibling worktrees have advanced unevenly: A01, A04, A06, and A09 have local commits;
A02/A03/A05/A07/A08 have unpublished worktree diffs.
Because most builder branches are still not visible through `origin`, they are current
local evidence for A00 monitoring but not ready-for-integration evidence. A03 is now
visible through `origin`, but it is still not a ready-for-integration candidate because
its consumed interfaces are unaccepted, owner docs are stale, the branch contains
A00-owned programme-file edits, real Hermes conformance is blocked, and newer local edits
are not pushed. The interface registry remains proposed-only.

A01, A02, A03, A04, A05, A06, A07, A08, and A09 now have local source/config/test drafts
or pushed A03 evidence.
They are not integration candidates yet. A01 has shared UUIDv7/Money/time/error/request
context, identity-table, identity API, service/channel enforcement, health, contract, and
redaction evidence with previous full backend tests passing, but its latest style commit
has only A00-observed ruff/mypy evidence because full pytest is currently blocked by host
disk capacity; A02 has durable inbox/job/trace/action services, a migration, realtime-email
durable acceptance, board-webhook durable ingress and dispatch, read-only Activity
trace/action endpoints, queue-worker rollout coverage, owner docs including PostgreSQL
migration-upgrade evidence, and focused checks passing, but now also touches broad legacy
service/connector/CS files outside the narrow durable-core boundary;
A03 has now pushed HermesBridge/tool catalog/invoker plus background-run/channel/conformance
fixtures, an honest native blocked stub, OpenClaw compat/dev transport, catalog MCP server,
browser chat-gateway allowlist/sanitization, a committed HTTP/SSE chat route,
compatibility matrix, pinned catalog/capability fixtures, and a conformance gate runner
that stays RED until real Hermes evidence exists, but still no real pinned-Hermes
conformance and stale owner docs; A04 has a local
committed connector slice with targeted tests passing; A05 has ticket lifecycle, CS-loop
lease, action-policy, WISMO shadow-draft, action-proposal, local attempt-execution,
approval, persisted autonomy-grant/pause, A02/A04 handoff-payload, state-surface,
state-API, attention, and quality-report evidence passing, but its focused mypy still fails
across state-surface, quality-report, and attention-event files; A06 has a committed theme/mobile-nav,
component-lab, operational-state, action/entity/evidence cards, and a11y tests passing,
but includes an A00-owned programme-file edit and whole-project frontend lint fails in
A07-owned brand UI; A07 has operator workspace backend and frontend tests passing but its
migration revises an older migration (`e2f9c6b4a1d3`) instead of the current baseline head
(`a0b1c2d3e4f5`); A08 has deterministic metric formula/model/read-model/service/API,
legacy-source, read-tool, daily-brief, daily-brief generation, and delivery-packet work
with its backend regression and targeted Finance frontend checks passing; it also has a
migration that revises current baseline head, an unmounted backend router, unregistered
route/nav/tool surfaces, and a duplicate Money type relative to A01; A09 has local
CI/security, System health, maintenance, backup/restore, release/update, extensions,
operational E2E, branch-readiness, and migration-head tooling, but the new branch-readiness
script is not ruff/mypy clean. These need owner pushes, exact verification evidence in
living docs, accepted dependencies, and A09 migration-head handling before queueing.

A03 and A06 have committed edits, and A04 has staged edits, to A00-owned files under
`docs/ecom-os/living/00-program/**`. A08 no longer shows a local A00-owned programme-file
edit in the current worktree status. A00 will not copy builder-owned programme files
blindly; any useful requests are reconciled into this branch by A00 only.

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
