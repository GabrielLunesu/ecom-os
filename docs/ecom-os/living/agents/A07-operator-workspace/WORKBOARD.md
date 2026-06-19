# A07 — Today, Tasks, Knowledge, and Operator Workspace — Workboard

## Implemented and verified

- Discovery inventory is complete at `3909904`.
- A07 backend workspace slice is implemented and locally verified:
  - `OperatorTask` with assignee/due/priority/status/entity links/comments/access labels/provenance.
  - Server-side task role filtering for list/get/update/comment paths using local access labels.
  - `BriefTaskInputRead` endpoint for A08 due/overdue task refs with access-filtered
    counts/titles, provenance, entity refs, and no comments.
  - `ToolCatalogManifest` endpoint for A03 task/document tool registration metadata with
    stable schema hash and no sensitive fields.
  - `KnowledgeDocument` versioning, access/trust labels, deterministic text/HTML extraction,
    unsupported extraction states, supersession, role-test retrieval, and Postgres FTS migration.
  - Deterministic attention ranking with explicit reasons and unavailable-source handling.
  - Replayable `AttentionSnapshot` persistence for Today normalized inputs and ranked
    outputs.
  - Safe Ask-Hermes launch intent schema/API that does not carry transcript/content/secrets.
- A07 frontend route-local slice is implemented and locally verified:
  - `/overview` creates replayable Today attention snapshots and renders snapshot metadata,
    deterministic attention items, ranking reasons, source state, and clickable source refs
    for known local surfaces plus Activity trace links when trace ids are present.
  - `/tasks` uses `OperatorTask` with board/list views, comments, entity links, access
    labels, task create access/brief controls, explicit role-scoped filtering, provenance,
    due dates, priorities, status changes, assignee/priority/due/access/brief update
    controls, and prepared Ask-Hermes launch intent metadata.
  - `/knowledge` uses `KnowledgeDocument` upsert plus explicit `/knowledge/role-test`
    retrieval with source/effective/type metadata, access and trust labels, supersession,
    ingestion/extraction state, snippets, evidence refs, role-filtered version body
    retrieval, and prepared Ask-Hermes launch intent metadata.
  - Today input composition fetches independent sources in parallel, degrades missing
    inputs as unavailable, and posts normalized inputs to `/attention/snapshots`.
  - Ask-Hermes buttons prepare safe A03 launch intents and show TTL/ref-count metadata
    without opening the non-canonical prototype chat route.

## Now

- Branch is being pushed for integration review as `ready_for_integration` by user
  instruction, with the verification caveats recorded in `VERIFICATION.md`.

## Next

1. Have A03 consume `/operator-workspace/tool-manifest` and
   `/operator-workspace/ask-hermes-intents` once A03 publishes its catalog/session launch contract.
2. Add A02 trace/evidence/tool invocation integration once the durable core contract is
   accepted.
3. Replace Today placeholder unavailable items with accepted A02/A05/A08 source adapters
   for approvals, incidents, failed/unknown actions, briefs, and metric snapshots.
4. Have A08 consume `/operator-workspace/brief/task-inputs` once A08 publishes its brief
   assembly contract.
5. Extend `/knowledge` extraction beyond markdown/text/HTML once binary document
   extraction scope is accepted.
6. Replace compatibility routes/pages (`/(ecom)/brand`, thin
   `team_tasks`) with redirects or facades only after preserving useful behavior and tests.

## Blocked

- Local A07 implementation is not blocked.
- Full integration still depends on accepted A01/A02/A03/A05/A06/A08 contracts listed in
  `INTERFACES.md`.
- Repo-wide gates have known non-A07 formatting failures and skipped final checks recorded
  in `VERIFICATION.md`.

## Exit condition

A07 can move to `ready_for_integration` only when:

- Build Spec Slice 9 and Slice 12 A07 criteria pass.
- Every Today item links to source/trace and has deterministic ranking reasons.
- Role-restricted cards and document search leak no counts, snippets, or content.
- Agent-created tasks include actor/run/trace provenance.
- Superseded SOP/document versions remain identifiable for historical trace inspection.
- Postgres full-text search works without mandatory embeddings.
- Contextual Ask Hermes opens/resumes canonical A03 sessions with safe entity references.
- A07 migrations and tests pass, and living docs contain exact verification evidence.
