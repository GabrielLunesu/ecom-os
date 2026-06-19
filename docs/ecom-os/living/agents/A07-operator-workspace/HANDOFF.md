# A07 — Today, Tasks, Knowledge, and Operator Workspace — Current Handoff

## Safe continuation point

Discovery, living-doc initialization, the A07 backend workspace slice, and route-local
frontend slice are complete on branch `agent/a07-chat`. The branch is being pushed for
integration review as `ready_for_integration` by user instruction; exact verification
evidence and skipped gates are in `VERIFICATION.md`.

## What is working

- `/overview` now creates and renders the route-local A07 Today attention snapshot from
  `useTodayAttention()`, with source links, local Activity trace links, item score,
  freshness when present, and unavailable dependency chips:
  `frontend/src/app/(ecom)/overview/page.tsx`.
- Legacy Ecom-OS `team_tasks` API still exists through `/api/v1/ecom/tasks`, but it no
  longer backs the current `/tasks` route:
  `backend/app/models/team_task.py`, `backend/app/services/team_tasks.py`,
  `backend/app/api/ecom.py`.
- Rich legacy board task system exists with useful fields/activity/dependencies:
  `backend/app/models/tasks.py`, `backend/app/api/tasks.py`, `frontend/src/app/boards/**`,
  and related backend/frontend tests.
- Prototype Brand vault works through `/api/v1/ecom/vault`:
  `backend/app/models/vault.py`, `backend/app/services/vault.py`,
  `frontend/src/app/(ecom)/brand/page.tsx`.
- Prototype read-only chat exists at `frontend/src/app/(ecom)/chat/page.tsx`, but this is
  not the v2 canonical Hermes chat.
- New A07 local backend contracts are working under
  `/api/v1/ecom/operator-workspace/*`:
  - tasks with entity links/comments/access labels/provenance and role-filtered reads;
  - A08-facing brief task inputs with due/overdue access-filtered task refs and no comments;
  - A03-facing tool manifest metadata with stable schema hash, risk metadata, and no
    sensitive fields;
  - knowledge documents with immutable versions, access/trust labels, FTS migration,
    deterministic text/HTML extraction, unsupported extraction states, supersession,
    and role-test retrieval;
  - deterministic attention ranking and replayable attention snapshots;
  - safe Ask-Hermes launch intents.
- New A07 frontend routes/helpers are working locally:
  - `/overview` as snapshot-backed Today attention queue with clickable known source refs
    and local Activity trace links;
  - `/tasks` against `OperatorTask`, with create access/brief controls and explicit
    role-scoped list/update/comment calls plus assignee/priority/due/access/brief update controls;
  - `/knowledge` against `KnowledgeDocument`, using explicit `/knowledge/role-test`
    retrieval for access-filtered results, upsert controls for source/effective date/type,
    and role-scoped document version body retrieval;
  - task/knowledge Ask-Hermes buttons prepare safe launch intents and show returned TTL/ref
    metadata without opening the prototype chat route;
  - `frontend/src/lib/ecom-api.ts` A07 helpers and
    `frontend/src/lib/ecom-operator-workspace.test.ts`.

## What remains

- See `WORKBOARD.md`.
- A03 consumption of `/api/v1/ecom/operator-workspace/tool-manifest`, tool registration,
  and actual contextual session launch are still pending.
- A07 prepares safe launch intents only; A03 still owns opening or resuming the canonical
  Hermes session.
- A02 durable trace/evidence/tool invocation integration is still pending.
- A07 attention snapshots are replay/debug artifacts only; A02 durable trace/evidence
  linkage is still pending.
- A08 consumption of `/api/v1/ecom/operator-workspace/brief/task-inputs` is still pending.
- Binary/PDF/DOCX extraction remains pending; unsupported types are visible as
  `extraction_status=unavailable` and are not searched.
- Decide whether legacy `team_tasks` should become a redirect/facade or be backfilled into
  `operator_tasks`.
- Targeted backend/frontend A07 lint/tests pass, A07 touched frontend files pass Prettier,
  and project-wide `tsc` passed. Full repo format/lint/type/migration readiness caveats
  are recorded in `VERIFICATION.md`.
- Frontend dev server is running in tmux session `ecom-a07-frontend` on
  `http://localhost:3000`; `/overview`, `/tasks`, and `/knowledge` returned HTTP 200.
  Stop it with `tmux kill-session -t ecom-a07-frontend`.

## Blockers and decisions

- See `RISKS.md` and `INTERFACES.md`.
- No hard blocker for local domain models, fixtures, and tests.
- Integration depends on pending A01/A02/A03/A05/A06/A08 contracts.
- A07 did not edit `docs/ecom-os/living/00-program/**`; A00 owns that folder.

## Commands to resume

Useful starting commands:

```bash
git status --short
rg -n "TeamTask|team_tasks|VaultDocument|vault_documents|Attention|Today|Knowledge" backend/app frontend/src backend/tests
rg -n "OperatorTask|KnowledgeDocument|rank_attention|operator-workspace" backend/app backend/tests
sed -n '1,260p' backend/app/models/team_task.py
sed -n '1,280p' backend/app/models/vault.py
sed -n '1,260p' frontend/src/app/\(ecom\)/tasks/page.tsx
```

Run targeted tests after writing the first A07 invariant tests:

```bash
cd backend
uv run pytest tests/test_operator_workspace.py
uv run python scripts/check_migration_graph.py
cd ../frontend
npx vitest run src/lib/ecom-operator-workspace.test.ts --coverage.enabled=false
```

## Do not accidentally regress

- Do not duplicate Hermes chat/session transport; A07 only emits safe contextual launch
  intents for A03.
- Do not calculate finance or daily brief numbers in A07; consume A08 snapshots and mark
  missing inputs unavailable.
- Do not own CS workflow/backlog semantics; consume A05 source contracts.
- Do not expose restricted document counts, snippets, titles, or content before access
  filtering.
- Do not require vector search; Postgres full-text search is the v1 baseline.
- Preserve useful task behavior from the legacy board task system where compatible:
  priority, due date, comments/activity, dependencies, status transitions, and tests.
- Preserve useful prototype vault behavior for seeded policy/SOP documents while adding
  immutable versions, access/trust labels, and supersession.
