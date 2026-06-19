---
owner: A07
branch: agent/a07-chat
status: ready_for_integration
last_verified_commit: 3909904 + uncommitted A07 backend/frontend workspace slice; final pushed SHA reported after commit
---

# A07 — Today, Tasks, Knowledge, and Operator Workspace — Current State

## Mission

Build the operator attention surface, tasks, document vault/search, contextual entity links, and Ask-Hermes entry points.

## Ownership

**Owns:** Today attention model/page, tasks domain/page/tools, documents/versions/access/search/Knowledge page, contextual chat launches and relevant settings UI.

**Does not own:** Hermes transport, finance formulas, CS workflow, connector normalization, global UI primitives.

## Current implementation

Verified at `3909904 + uncommitted A07 backend/frontend workspace slice` in
`/Users/gabriellunesu/Git/ecom-os-worktrees/a07-chat`.

The current implementation is useful prototype input, not yet the v2 A07 contract.

### A07 backend workspace slice

Implemented in this branch:

- New A07 models in `backend/app/models/operator_workspace.py`:
  - `OperatorTask`, `OperatorTaskEntityLink`, `OperatorTaskComment`;
  - `KnowledgeDocument`, `KnowledgeDocumentVersion`, `KnowledgeDocumentChunk`;
  - `AttentionSnapshot`.
- New migration `backend/migrations/versions/a07_20260619_operator_workspace.py`
  creates A07 task, document/version/chunk, FTS index for Postgres, and attention snapshot
  tables. It revises current head `a0b1c2d3e4f5`, leaving a single Alembic head.
- New schemas in `backend/app/schemas/operator_workspace.py` define task provenance,
  task access labels, A08-facing brief task inputs, document access/trust/search payloads,
  deterministic attention inputs/results/snapshots, A03-facing tool catalog manifest
  metadata, and safe `AskHermesLaunchRequest`/`AskHermesLaunchIntent`.
- New service code in `backend/app/services/operator_workspace.py` implements:
  - agent task provenance validation at schema/service boundary;
  - task entity links, comments, access labels, and role-filtered task reads;
  - access-filtered due/overdue task inputs for A08 daily brief assembly;
  - immutable document versions with checksum, supersession, deterministic extraction
    status, and chunks;
  - markdown/plain-text extraction, visible-text HTML extraction that ignores
    active/metadata content, and `unavailable` extraction state for unsupported types;
  - role-filtered document retrieval before counts/snippets/content;
  - Postgres FTS path with SQLite fallback for tests;
  - deterministic attention ranking with source-status reasons and replayable
    `AttentionSnapshot` persistence for normalized inputs plus ranked outputs;
  - local tool manifest generation with stable schema hash for A03 adapter/MCP catalog work;
  - safe Ask-Hermes launch intent creation without content/transcript/credentials.
- New API router `backend/app/api/operator_workspace.py` is mounted under existing
  authenticated `/api/v1/ecom/operator-workspace/*` through `backend/app/api/ecom.py`.
  This exposes local A07 endpoints but does not execute Hermes chat transport.
- New tests in `backend/tests/test_operator_workspace.py` cover agent provenance,
  task links/comments, task access filtering, brief task input filtering, restricted
  document search leakage, HTML active-content extraction filtering, unsupported
  document extraction state, supersession retrieval, deterministic attention
  ranking/unavailable-not-zero, attention snapshot replay, safe Ask-Hermes intent shape,
  and tool manifest metadata.

### A07 frontend workspace slice

Implemented in this branch:

- `frontend/src/lib/ecom-api.ts` now has typed local A07 client helpers for:
  - `OperatorTask` list/create/update/comment;
  - `KnowledgeDocument` search/upsert and explicit `/knowledge/role-test` retrieval;
  - deterministic attention ranking and replayable attention snapshot creation;
  - safe Ask-Hermes launch intent creation;
  - `fetchTodayAttention()` which fetches tasks, connection health, legacy metrics,
    tickets, and insights in parallel, then sends normalized inputs to the backend snapshot
    endpoint so the visible Today queue has a replayable record.
- `frontend/src/app/(ecom)/overview/page.tsx` is now the route-local Today surface. It
  renders snapshot metadata plus ranked attention items with severity, source status,
  coverage, deterministic score, freshness when present, ranking reasons, clickable
  source refs for known source types, Activity links for trace ids where present, and
  per-item unavailable dependency chips for missing A02/A05/A08 sources.
- `frontend/src/app/(ecom)/tasks/page.tsx` now uses the A07 `OperatorTask` API. It supports
  board/list views, assignee labels, due dates, priority, status changes, assignee/
  priority/due/access/brief update controls, entity links, comments, role-scoped
  server-side filtering, task create controls for `access_label` and
  `daily_brief_include`, access-label display, provenance display, trace indication, and
  safe Ask-Hermes intent preparation. The UI stores the returned intent metadata and shows
  TTL plus entity-ref count without opening chat transport.
- `frontend/src/app/(ecom)/knowledge/page.tsx` is a new A07-owned Knowledge route. It
  supports search through the explicit role-test endpoint, accessible result counts after
  access filtering, source/effective metadata display, document type selection,
  access/trust labels, supersession/ingestion/extraction states, document version upsert,
  role-filtered document version body retrieval, and safe Ask-Hermes intent preparation
  without document body transfer.
- `frontend/src/lib/ecom-operator-workspace.test.ts` covers Today input composition and
  snapshot persistence:
  failed task/CS sources become unavailable items, due task source refs keep trace links,
  health source refs are surfaced, and metrics are consumed as source signals while A08
  metric snapshots remain pending. The focused snapshot test verifies `fetchTodayAttention()`
  posts normalized inputs to `/attention/snapshots` and consumes the returned replay payload.
  The focused launch-intent test verifies the frontend sends no body/content/transcript or
  credential keys when preparing an A03 launch intent. The focused role-test test verifies
  the client posts `{ role, query }` to `/knowledge/role-test` and consumes access-filtered
  counts/results. The focused task role test verifies task list requests carry an explicit
  role query parameter for server-side access-label filtering. The focused task create test
  verifies `access_label`, `daily_brief_include`, and entity links are sent in the create
  payload. The focused knowledge upsert test verifies `source`, `document_type`,
  `effective_date`, access label, and trust label are sent in the document version payload.
  The focused document get test verifies a specific version is fetched with an explicit
  role query before body/version metadata is rendered. The focused source-link test
  verifies Today source refs route to existing Ecom surfaces while unavailable dependency
  refs remain unlinked. The focused trace-link test verifies Today trace ids link to the
  local Activity surface while A02 durable trace explorer integration remains pending. The
  focused task update test verifies role-scoped updates for assignee, priority, due date,
  access label, and brief inclusion. The focused item-evidence helper test verifies
  unavailable dependency normalization and freshness display fallback.

### Today / Overview

- Existing route: `frontend/src/app/(ecom)/overview/page.tsx`.
- Current behavior: renders A07 Today attention snapshots from `useTodayAttention()`,
  composed from local/pending source contracts and persisted through
  `create_attention_snapshot()`, which ranks with `rank_attention()` before storing the
  normalized inputs and ranked outputs.
  Known Today source references link to local source surfaces such as `/tasks`, `/cs`,
  `/settings`, `/analytics`, `/overview`, and `/knowledge`; missing dependency refs stay
  plain because they are unavailable, not source evidence. Trace ids link to
  `/activity?trace=...` as a local debug bridge until A02 publishes the durable trace
  explorer route.
- Backend sources: `backend/app/api/ecom.py` `/ecom/metrics` and `/ecom/insights`, with
  service code under `backend/app/services/metrics.py` and `backend/app/services/insights.py`.
- Current state: route-local A07 implementation. It composes due tasks, connection health,
  CS backlog, legacy metric signals, insights, and explicit unavailable placeholders for
  pending approvals/incidents/actions/briefs. The frontend now creates replayable attention
  snapshots through `/api/v1/ecom/operator-workspace/attention/snapshots` and displays the
  snapshot id, source status, input count, item count, window, item score, freshness when
  present, and per-item unavailable dependencies.
- Remaining gap: accepted A02/A05/A08 source contracts for real approvals, incidents,
  failed/unknown actions, daily briefs, and metric snapshots.

### Tasks

- Existing rich task model/API: `backend/app/models/tasks.py`, `backend/app/api/tasks.py`,
  `backend/app/schemas/tasks.py`, and board route UI under `frontend/src/app/boards/**`.
  This includes status, priority, due date, creator, assigned agent, auto-created flag,
  comments/activity, dependencies, tags, custom fields, approval links, SSE streams, and
  tests such as `backend/tests/test_tasks_api_rows.py`,
  `backend/tests/test_task_dependencies_integration.py`, and
  `backend/tests/test_approval_task_links.py`.
- Existing Ecom-OS team task model/API: `backend/app/models/team_task.py`,
  `backend/app/services/team_tasks.py`, `/api/v1/ecom/tasks` in `backend/app/api/ecom.py`,
  migration `backend/migrations/versions/c6d7e8f9a0b1_add_team_tasks.py`, frontend
  route `frontend/src/app/(ecom)/tasks/page.tsx`, and client helpers in
  `frontend/src/lib/ecom-api.ts`.
- Current behavior: `/tasks` now uses `/api/v1/ecom/operator-workspace/tasks` and supports
  assignee labels, due dates, priority, status, entity links, comments, task access labels,
  daily brief inclusion control, assignee/priority/due/access/brief update controls,
  provenance, trace indication, an explicit role selector, and safe Ask-Hermes launch intent
  preparation. Task list/get/update and comment endpoints apply local
  role-to-access-label filtering server-side, and the frontend now sends that role for
  list/update/comment calls. A07 also exposes
  `/api/v1/ecom/operator-workspace/brief/task-inputs` for A08 to read due/overdue brief
  task references without comments or inaccessible titles.
- Current state: two competing historical task shapes still exist. The board-scoped `tasks` implementation
  has reusable fields and behavior but is tied to legacy board/organization concepts.
  `team_tasks` is closer to the old Ecom-OS route but too thin for v2 and no longer backs
  the current `/tasks` page.
- Remaining gap: accepted A01 identity/access-label contract for assignee/user roles,
  A02 trace/evidence persistence, A03 consumption/registration of the local
  `/tool-manifest`, A08 consumption of the local brief task input, and a deliberate
  migration/facade decision for the old `team_tasks` and board task systems.

### Knowledge / Document Vault

- Existing model/service/API: `backend/app/models/vault.py`, `backend/app/services/vault.py`,
  `/api/v1/ecom/vault` in `backend/app/api/ecom.py`, migration
  `backend/migrations/versions/e2f3a4b5c6d7_add_vault_documents.py`, frontend route
  `frontend/src/app/(ecom)/brand/page.tsx`, and client helpers in `frontend/src/lib/ecom-api.ts`.
- Current behavior: seeded markdown documents for shipping/privacy policy; list/get/upsert
  by `slug`; keyword search over title/tags/body for CS runtime usage.
- Current state: compatibility facade only. It stores one mutable body per slug and exposes
  body content through the Brand page.
- Remaining gap: A01 role model integration, A02 evidence records, richer extractor
  pipeline for binary/document attachments, and A03 tool catalog registration.
  The new knowledge path and `/knowledge` page now cover logical paths, immutable versions,
  source/effective date/owner metadata, access/trust labels, extraction status, Postgres
  FTS migration, supersession, role-test retrieval, deterministic HTML/text extraction,
  and unsupported extraction states without requiring a vector DB.

### Contextual Ask Hermes

- Existing route: `frontend/src/app/(ecom)/chat/page.tsx`; existing backend endpoint:
  `/api/v1/ecom/chat` in `backend/app/api/ecom.py`; existing service:
  `backend/app/services/chat.py`.
- Current behavior: read-only copilot over Shopify/vault data with local message state.
- Current state: not canonical v2 Hermes chat. A03 owns HermesBridge, chat route, session
  creation/resume/history, tool streaming, and browser-safe protocol mediation.
- A07 now exposes safe launch intent construction/API shape only. A03 still owns opening
  or resuming canonical Hermes sessions. The A07 UI labels this as prepared intent metadata
  rather than an opened Hermes chat.

### Current source ownership map for A07 work

- A07-owned or A07-candidate source: task domain/service/API to be introduced or migrated,
  document/search domain/service/API, Today attention model/API, frontend routes `/`,
  `/tasks`, `/knowledge`, and A07-owned tests/migrations.
- Shared/other-owner files not to edit directly before accepted registration: central
  router wiring in `backend/app/main.py`, generated frontend clients, global nav/sidebar,
  package/lock files, A03 chat route/transport, A08 finance/brief formulas, A05 CS/autonomy
  workflow, A02 trace/action core, A01 identity/contracts, and A06 global primitives.

## Current architecture

See `DIAGRAMS.md`.

Current architecture includes the prototype monolith path plus the new A07 backend slice:

```text
frontend /(ecom)/overview,tasks,brand,chat
  -> frontend/src/lib/ecom-api.ts
  -> backend/app/api/ecom.py
  -> backend/app/services/{team_tasks,vault,metrics,insights,chat}.py
  -> legacy tables team_tasks, vault_documents, orders/tickets/insights

backend/app/api/ecom.py
  -> backend/app/api/operator_workspace.py
  -> backend/app/services/operator_workspace.py
  -> operator_tasks/operator_task_comments/operator_task_entity_links
  -> /operator-workspace/brief/task-inputs for A08 task refs
  -> /operator-workspace/tool-manifest for A03 catalog metadata
  -> /operator-workspace/attention/snapshots for replayable Today rankings
  -> knowledge_documents/knowledge_document_versions/knowledge_document_chunks
  -> attention_snapshots

frontend /(ecom)/overview,tasks,knowledge
  -> frontend/src/lib/ecom-api.ts A07 helpers
  -> /api/v1/ecom/operator-workspace/*
```

This path is authenticated by the route dependency, but it does not yet carry v2 trace
context through A02 durable records, durable tool invocation records, generated A03 tool
catalog registration, or accepted A03 contextual Hermes launch execution semantics.

## Dependencies

Consumes A01 identity/request/access labels, A02 trace/action/evidence/incidents/jobs,
A03 contextual Hermes launch/tool registration, A05 CS attention/backlog sources, A06 UI
states/primitives, and A08 brief/metric snapshots.

Until those contracts are accepted, A07 will proceed with typed local ports and fixtures:
identity and access filters return deterministic fake scopes; trace/source links use
nullable references; missing A05/A08/A02 inputs are represented as `unavailable`, never
as zero.
