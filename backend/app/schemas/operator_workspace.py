"""Schemas for A07 operator workspace contracts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.schemas.common import NonEmptyStr

TaskStatus = Literal["todo", "doing", "blocked", "done", "cancelled"]
TaskPriority = Literal["low", "normal", "high", "urgent"]
TaskProvenance = Literal["human", "agent"]
AssigneeType = Literal["unassigned", "user", "hermes_profile", "external"]

AccessLabel = Literal["public", "operations", "cs", "finance", "founder_private"]
TrustLabel = Literal["operator_supplied", "imported", "verified", "untrusted"]
ExtractionStatus = Literal["pending", "indexed", "failed", "unavailable"]

AttentionSourceStatus = Literal["available", "partial", "stale", "unavailable"]
AttentionSeverity = Literal["critical", "high", "medium", "low", "info"]
AttentionCoverage = Literal["verified", "observed", "imported", "unknown"]


class EntityLinkIn(SQLModel):
    """Safe entity reference attached to a task or chat launch."""

    entity_type: NonEmptyStr
    entity_id: NonEmptyStr
    label: str = ""
    trace_id: UUID | None = None


class EntityLinkRead(EntityLinkIn):
    id: UUID


class OperatorTaskCreate(SQLModel):
    """Create a v2 operator task."""

    title: NonEmptyStr
    description: str | None = None
    status: TaskStatus = "todo"
    priority: TaskPriority = "normal"
    due_at: datetime | None = None
    assignee_type: AssigneeType = "unassigned"
    assignee_id: UUID | None = None
    assignee_label: str = ""
    provenance: TaskProvenance = "human"
    created_by_actor_type: NonEmptyStr = "user"
    created_by_actor_id: UUID | None = None
    source_trace_id: UUID | None = None
    source_run_id: UUID | None = None
    source_evidence_ref: str | None = None
    access_label: AccessLabel = "operations"
    daily_brief_include: bool = True
    entity_links: list[EntityLinkIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_agent_provenance(self) -> "OperatorTaskCreate":
        """Agent-created tasks must be attributable to a run and trace."""
        if self.provenance == "agent" and (
            self.created_by_actor_id is None
            or self.source_trace_id is None
            or self.source_run_id is None
        ):
            raise ValueError(
                "agent-created tasks require created_by_actor_id, source_trace_id, and source_run_id"
            )
        return self


class OperatorTaskUpdate(SQLModel):
    title: NonEmptyStr | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    assignee_type: AssigneeType | None = None
    assignee_id: UUID | None = None
    assignee_label: str | None = None
    access_label: AccessLabel | None = None
    daily_brief_include: bool | None = None


class OperatorTaskCommentCreate(SQLModel):
    body: NonEmptyStr
    actor_type: NonEmptyStr = "user"
    actor_id: UUID | None = None
    trace_id: UUID | None = None


class OperatorTaskCommentRead(SQLModel):
    id: UUID
    body: str
    actor_type: str
    actor_id: UUID | None
    trace_id: UUID | None
    created_at: datetime


class OperatorTaskRead(SQLModel):
    id: UUID
    brand_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_at: datetime | None
    assignee_type: str
    assignee_id: UUID | None
    assignee_label: str
    provenance: str
    created_by_actor_type: str
    created_by_actor_id: UUID | None
    source_trace_id: UUID | None
    source_run_id: UUID | None
    source_evidence_ref: str | None
    access_label: str
    daily_brief_include: bool
    entity_links: list[EntityLinkRead] = Field(default_factory=list)
    comments: list[OperatorTaskCommentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BriefTaskRef(SQLModel):
    """Access-filtered task reference for deterministic daily brief inputs."""

    task_id: UUID
    title: str
    status: str
    priority: str
    due_at: datetime | None
    overdue: bool
    assignee_type: str
    assignee_id: UUID | None
    assignee_label: str
    provenance: str
    access_label: str
    source_trace_id: UUID | None
    source_run_id: UUID | None
    source_evidence_ref: str | None
    entity_links: list[EntityLinkRead] = Field(default_factory=list)
    summary: str


class BriefTaskInputRead(SQLModel):
    """A07 task section input for A08 deterministic daily briefs."""

    role: str
    source_status: AttentionSourceStatus = "available"
    coverage: AttentionCoverage = "verified"
    generated_at: datetime
    horizon_end: datetime
    accessible_count: int
    tasks: list[BriefTaskRef] = Field(default_factory=list)


class KnowledgeDocumentUpsert(SQLModel):
    logical_path: NonEmptyStr
    title: NonEmptyStr
    body: str
    document_type: str = "markdown"
    source: str = "operator"
    owner_actor_type: str = "user"
    owner_actor_id: UUID | None = None
    access_label: AccessLabel = "operations"
    trust_label: TrustLabel = "operator_supplied"
    effective_date: date | None = None
    source_trace_id: UUID | None = None

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        return value or ""


class KnowledgeDocumentSearchResult(SQLModel):
    document_id: UUID
    version_id: UUID
    title: str
    logical_path: str
    source: str
    effective_date: date | None
    access_label: str
    trust_label: str
    supersession_state: str
    snippet: str | None
    evidence_ref: str
    ingestion_status: str
    extraction_status: str


class KnowledgeDocumentRead(KnowledgeDocumentSearchResult):
    body: str
    version_number: int
    supersedes_version_id: UUID | None
    checksum: str
    created_at: datetime


class KnowledgeRoleTest(SQLModel):
    role: str
    query: str


class AttentionSourceRef(SQLModel):
    type: str
    id: str
    label: str = ""


class AttentionInput(SQLModel):
    """Normalized upstream signal used by deterministic Today ranking."""

    kind: str
    id: str
    title: str
    summary: str = ""
    severity: AttentionSeverity = "info"
    source_status: AttentionSourceStatus = "available"
    coverage: AttentionCoverage = "unknown"
    trace_id: UUID | None = None
    source_refs: list[AttentionSourceRef] = Field(default_factory=list)
    freshness_as_of: datetime | None = None
    primary_action: str | None = None
    reasons: list[str] = Field(default_factory=list)


class AttentionItemRead(AttentionInput):
    rank: int
    score: int
    unavailable_dependencies: list[str] = Field(default_factory=list)


class AttentionSnapshotCreate(SQLModel):
    """Persist normalized Today inputs and deterministic ranked output for replay."""

    inputs: list[AttentionInput] = Field(default_factory=list)
    window_start: datetime | None = None
    window_end: datetime | None = None


class AttentionSnapshotRead(SQLModel):
    id: UUID
    brand_id: UUID
    status: str
    source_status: str
    window_start: datetime | None
    window_end: datetime | None
    input_count: int
    item_count: int
    inputs: list[AttentionInput] = Field(default_factory=list)
    items: list[AttentionItemRead] = Field(default_factory=list)
    created_at: datetime


class AskHermesLaunchIntent(SQLModel):
    surface: str
    entity_refs: list[EntityLinkIn] = Field(default_factory=list)
    trace_id: UUID | None = None
    suggested_prompt: str
    access_label: AccessLabel = "operations"
    ttl_seconds: int = 600


class AskHermesLaunchRequest(SQLModel):
    surface: NonEmptyStr
    entity_refs: list[EntityLinkIn] = Field(default_factory=list)
    trace_id: UUID | None = None
    suggested_prompt: NonEmptyStr
    access_label: AccessLabel = "operations"


class ToolCatalogEntry(SQLModel):
    """A07-owned tool metadata for A03 catalog registration."""

    name: str
    version: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    read_or_write: Literal["read", "write"]
    risk_class: str
    required_ecom_permissions: list[str] = Field(default_factory=list)
    required_connection_types: list[str] = Field(default_factory=list)
    store_scope_rule: str
    supports_simulation: bool
    supports_idempotency: bool
    reconciliation_strategy: str
    sensitive_fields: list[str] = Field(default_factory=list)
    minimum_trace_coverage: AttentionCoverage


class ToolCatalogManifest(SQLModel):
    """Stable A07 manifest for A03 adapter/MCP catalog generation."""

    namespace: str = "a07.operator_workspace"
    version: str
    schema_hash: str
    tools: list[ToolCatalogEntry]
