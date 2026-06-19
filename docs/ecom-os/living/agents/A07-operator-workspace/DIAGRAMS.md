# A07 — Today, Tasks, Knowledge, and Operator Workspace — Diagrams

## Current

```mermaid
flowchart LR
  UI1["/(ecom)/overview"] --> API["backend/app/api/ecom.py"]
  UI2["/(ecom)/tasks"] --> Client["frontend/src/lib/ecom-api.ts"]
  UI3["/(ecom)/brand"] --> Client
  UI4["/(ecom)/chat"] --> Client
  Client --> API
  API --> TeamSvc["services/team_tasks.py"]
  API --> VaultSvc["services/vault.py"]
  API --> MetricsSvc["services/metrics.py"]
  API --> ChatSvc["services/chat.py"]
  TeamSvc --> TeamTable["team_tasks"]
  VaultSvc --> VaultTable["vault_documents"]
  MetricsSvc --> CommerceTables["legacy commerce/ticket tables"]
  ChatSvc --> VaultTable
  ChatSvc --> CommerceTables
  API --> WorkspaceAPI["api/operator_workspace.py"]
  WorkspaceAPI --> WorkspaceSvc["services/operator_workspace.py"]
  WorkspaceSvc --> WorkspaceTables["operator_* / knowledge_* / attention_snapshots"]
  WorkspaceSvc --> BriefInput["Brief task input\naccess-filtered due tasks"]
  WorkspaceSvc --> ToolManifest["Tool manifest\nA03 catalog metadata"]
  WorkspaceSvc --> AttentionSnapshot["Attention snapshots\ninputs + ranked items"]
  UI1 --> WorkspaceClient["ecom-api.ts A07 helpers"]
  UI2 --> WorkspaceClient
  KnowledgeUI["/(ecom)/knowledge"] --> WorkspaceClient
  WorkspaceClient --> WorkspaceAPI
```

## Target

```mermaid
flowchart TB
  subgraph Browser["Browser - no privileged credentials"]
    Today["/ Today"]
    Tasks["/tasks"]
    Knowledge["/knowledge"]
    Ask["Ask Hermes buttons"]
  end

  subgraph A07["A07 backend domain"]
    Attention["AttentionService\nrank + reasons"]
    AttentionSnapshot["AttentionSnapshot\nreplayable rank state"]
    TaskSvc["TaskService\nassignee/due/priority/status/comments/provenance"]
    BriefInput["BriefTaskInput\naccess-filtered due/overdue refs"]
    DocSvc["DocumentService\nversions/access/trust/FTS/supersession"]
    ToolManifest["ToolCatalogManifest\nversion + schema hash"]
    Launch["AskHermesLaunchIntent\nsafe entity refs only"]
  end

  subgraph A07DB["A07 Postgres-owned records"]
    TaskTables["tasks/comments/entity_links/provenance"]
    DocTables["documents/document_versions/document_chunks_fts"]
    AttentionTables["optional attention snapshots/source state"]
  end

  subgraph Providers["Consumed contracts"]
    A01["A01 identity + access labels"]
    A02["A02 traces/actions/evidence/incidents"]
    A03["A03 HermesBridge/session launch/tool catalog"]
    A05["A05 CS backlog/needs_rep signals"]
    A08["A08 brief/metric snapshots"]
    A06["A06 UI states/primitives"]
  end

  Today --> Attention
  Attention --> AttentionSnapshot
  Tasks --> TaskSvc
  BriefInput --> TaskSvc
  Knowledge --> DocSvc
  Ask --> Launch
  ToolManifest --> A03

  TaskSvc --> TaskTables
  DocSvc --> DocTables
  Attention --> AttentionTables

  Attention --> A02
  Attention --> A05
  Attention --> A08
  Attention --> TaskSvc
  TaskSvc --> A01
  TaskSvc --> A02
  BriefInput --> A08
  DocSvc --> A01
  DocSvc --> A02
  Launch --> A03
  Today --> A06
  Tasks --> A06
  Knowledge --> A06
```

Failure paths:

- Missing A02/A05/A08 source: Attention item source state is `unavailable`; no zero count
  is inferred.
- Restricted document/task source: A01 access filter removes it before counts/snippets.
- Hermes unavailable or A03 contract absent: Ask Hermes action is disabled/degraded; A07
  does not open its own chat session.
- FTS extractor unavailable: document record remains with `ingestion_status` and visible
  degraded state; no vector DB is required.
