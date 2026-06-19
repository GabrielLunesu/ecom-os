# A07 — Today, Tasks, Knowledge, and Operator Workspace — Interfaces

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| TaskService / task API | local v0 implemented | `backend/app/services/operator_workspace.py`, `backend/app/api/operator_workspace.py`, `backend/app/schemas/operator_workspace.py`, `frontend/src/app/(ecom)/tasks/page.tsx` | A03 tools, A08 brief, Today UI, Knowledge/entity context | Validation/forbidden/not-found are typed. Agent-created tasks without provenance are rejected. Task list/get/update/comment paths filter by role-derived access labels before returning task data; inaccessible task reads collapse to not-found. Missing trace source is allowed only for human-created tasks and is explicit. |
| DocumentSearch / DocumentGet | local v0 implemented | `backend/app/services/operator_workspace.py`, `backend/app/api/operator_workspace.py`, `backend/app/schemas/operator_workspace.py`, `frontend/src/app/(ecom)/knowledge/page.tsx` | A03 document tools, Today UI, Knowledge UI, trace evidence views | Access filtering runs before counts/snippets/content. `not_found` and `inaccessible` intentionally collapse at API boundary to avoid existence leaks; ingestion/extraction status is explicit for accessible docs. |
| AttentionItem / AttentionExplanation | local v0 implemented | `rank_attention()`, `AttentionInput`/`AttentionItemRead`, `frontend/src/app/(ecom)/overview/page.tsx`, `buildTodayAttentionInputs()` | Today UI, A03 contextual launch, A08 brief consumption if needed | Missing upstream inputs are `unavailable`, not zero. Items without source/trace carry coverage/reasons. Ordering and score are deterministic. The UI renders source state, score, freshness when present, reasons, source refs, trace refs, and unavailable dependency chips. |
| AttentionSnapshot | local v0 implemented | `AttentionSnapshotCreate`/`AttentionSnapshotRead`, `create_attention_snapshot()`, and `/attention/snapshots` | Today UI, trace/debug views, future A02 evidence linkage | Persists normalized inputs and deterministic ranked items for replay. This is not an A02 durable trace substitute; source refs and nullable trace ids remain explicit. |
| Brief task input | local v0 implemented, A08 acceptance pending | `BriefTaskInputRead`/`BriefTaskRef`, `brief_task_inputs()`, and `/brief/task-inputs` | A08 daily brief | Returns due/overdue task references with provenance, entity refs, source trace refs, and access-filtered summaries. Counts/titles are computed after role filtering. Comments and task bodies are not included. |
| A07 tool manifest | local v0 implemented, A03 acceptance pending | `ToolCatalogManifest`/`ToolCatalogEntry`, `operator_workspace_tool_manifest()`, and `/tool-manifest` | A03 adapter/MCP catalog generation | Exposes task/document read tools, internal task create, and safe launch-intent builder with version, schema hash, required metadata, risk classification, no connection requirements, and no sensitive fields. Does not register tools or open Hermes sessions. |
| AskHermesLaunchIntent for A07 entities | local v0 implemented, A03 acceptance pending | `AskHermesLaunchRequest`/`AskHermesLaunchIntent` and `/ask-hermes-intents` | A03 Hermes chat | Contains only safe entity refs, labels, access labels, and optional trace refs. No transcript, document body, restricted snippets, or service credential. |

### Proposed local shapes

```text
TaskRef {
  id, title, status, priority, due_at, assignee_ref,
  entity_links[], provenance, access_label, trace_id?, source_evidence[], permissions
}

BriefTaskInput {
  role, source_status, coverage, generated_at, horizon_end,
  accessible_count, tasks: BriefTaskRef[]
}

DocumentSearchResult {
  document_id, version_id, title, source, effective_date, access_label,
  trust_label, supersession_state, snippet?, evidence_ref, ingestion_status
}

AttentionItem {
  id, kind, severity, rank, title, summary, source_refs[], trace_id?,
  freshness, coverage, reasons[], primary_action, unavailable_dependencies[]
}

AttentionSnapshot {
  id, status, source_status, input_count, item_count, inputs[], items[]
}

AskHermesLaunchIntent {
  surface, entity_refs[], trace_id?, suggested_prompt, access_label, ttl_seconds
}

ToolCatalogManifest {
  namespace, version, schema_hash, tools[]
}
```

## Consumes

| Interface | Owner | Required version/status | Call sites | Fallback/degraded behavior |
|---|---|---|---|---|
| Identity/request/access labels | A01 | pending accepted contract | Task/document/attention APIs and UI permissions | Use local fake actor/access fixtures in isolated tests; production integration blocks until accepted. |
| Trace/action/evidence/incidents/jobs | A02 | pending accepted contract | Task provenance, document evidence, Today failed/unknown actions/incidents, trace links | Nullable trace refs in local model; attention cards show `unavailable` for missing A02 sources. |
| Hermes contextual session launch and tool catalog registration | A03 | pending accepted contract | Ask-Hermes buttons; task/document tool exposure | Generate launch intents and local tool manifest locally; do not open chat transport directly. A03 registration remains pending. |
| CS attention/backlog source | A05 | pending accepted contract | Today tickets-needing-rep, backlog growth, CS source links | Source block is `unavailable`; do not display zero tickets or hidden restricted counts. |
| UI primitives/states/shell | A06 | pending accepted contract | `/`, `/tasks`, `/knowledge` | Use existing minimal components only for prototypes; integration UI blocks until A06 contract exists. |
| Metric snapshot and daily brief status | A08 | pending accepted contract | Today brief/metric signals; brief task input integration | Metric/brief sections are `unavailable`; never compute finance numbers in A07. |

## Open requests

No programme `INTERFACE-REQUESTS.md` edit has been made from this branch because A00 owns
`docs/ecom-os/living/00-program/**`. Requests to publish there after A00/A09 coordination:

| Request | Owner | Need |
|---|---|---|
| A07-REQ-01 | A03 | Accept `AskHermesLaunchIntent` and task/document contextual launch behavior. |
| A07-REQ-02 | A03 | Accept task/document read tool catalog registration path and schema ownership. |
| A07-REQ-03 | A02 | Accept trace/evidence/source reference envelope used by tasks, documents, and attention items. |
| A07-REQ-04 | A05 | Publish CS attention source with access-filtered counts and source links. |
| A07-REQ-05 | A08 | Publish brief status and metric signal source with freshness/coverage and no A07 calculation. |
| A07-REQ-06 | A06 | Publish route state primitives for loading/empty/stale/partial/unavailable/permission/error. |
