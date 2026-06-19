"""A07 operator workspace models for tasks, documents, and attention."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class OperatorTask(QueryModel, table=True):
    """Canonical A07 task with provenance and source trace references."""

    __tablename__ = "operator_tasks"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    title: str = Field(index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    status: str = Field(default="todo", index=True)
    priority: str = Field(default="normal", index=True)
    due_at: datetime | None = Field(default=None, index=True)

    assignee_type: str = Field(default="unassigned", index=True)
    assignee_id: UUID | None = Field(default=None, index=True)
    assignee_label: str = Field(default="")

    provenance: str = Field(default="human", index=True)
    created_by_actor_type: str = Field(default="user", index=True)
    created_by_actor_id: UUID | None = Field(default=None, index=True)
    source_trace_id: UUID | None = Field(default=None, index=True)
    source_run_id: UUID | None = Field(default=None, index=True)
    source_evidence_ref: str | None = Field(default=None, max_length=256)
    access_label: str = Field(default="operations", index=True)
    daily_brief_include: bool = Field(default=True, index=True)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class OperatorTaskEntityLink(QueryModel, table=True):
    """Typed entity reference attached to an operator task."""

    __tablename__ = "operator_task_entity_links"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="operator_tasks.id", index=True)
    entity_type: str = Field(index=True)
    entity_id: str = Field(index=True)
    label: str = Field(default="")
    trace_id: UUID | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class OperatorTaskComment(QueryModel, table=True):
    """Comment/activity entry for an operator task."""

    __tablename__ = "operator_task_comments"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="operator_tasks.id", index=True)
    actor_type: str = Field(default="user", index=True)
    actor_id: UUID | None = Field(default=None, index=True)
    body: str = Field(sa_column=Column(Text))
    trace_id: UUID | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class KnowledgeDocument(QueryModel, table=True):
    """Logical document record with access, trust, and version state."""

    __tablename__ = "knowledge_documents"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    logical_path: str = Field(index=True)
    title: str = Field(index=True)
    document_type: str = Field(default="markdown", index=True)
    source: str = Field(default="operator", index=True)
    owner_actor_type: str = Field(default="user", index=True)
    owner_actor_id: UUID | None = Field(default=None, index=True)
    access_label: str = Field(default="operations", index=True)
    trust_label: str = Field(default="operator_supplied", index=True)
    current_version_id: UUID | None = Field(default=None, index=True)
    effective_date: date | None = Field(default=None, index=True)
    expires_at: datetime | None = Field(default=None, sa_column=Column(DateTime, index=True))
    ingestion_status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class KnowledgeDocumentVersion(QueryModel, table=True):
    """Immutable content version for a knowledge document."""

    __tablename__ = "knowledge_document_versions"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="knowledge_documents.id", index=True)
    version_number: int = Field(index=True)
    body: str = Field(sa_column=Column(Text))
    checksum: str = Field(index=True)
    extracted_text: str = Field(default="", sa_column=Column(Text))
    extraction_status: str = Field(default="pending", index=True)
    supersedes_version_id: UUID | None = Field(default=None, index=True)
    source_trace_id: UUID | None = Field(default=None, index=True)
    created_by_actor_type: str = Field(default="user", index=True)
    created_by_actor_id: UUID | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class KnowledgeDocumentChunk(QueryModel, table=True):
    """Searchable document chunk retaining version provenance."""

    __tablename__ = "knowledge_document_chunks"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="knowledge_documents.id", index=True)
    version_id: UUID = Field(foreign_key="knowledge_document_versions.id", index=True)
    chunk_index: int = Field(default=0, index=True)
    text: str = Field(sa_column=Column(Text))
    access_label: str = Field(default="operations", index=True)
    trust_label: str = Field(default="operator_supplied", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class AttentionSnapshot(QueryModel, table=True):
    """Optional deterministic Today snapshot for replay/debugging."""

    __tablename__ = "attention_snapshots"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    status: str = Field(default="draft", index=True)
    source_status: str = Field(default="available", index=True)
    window_start: datetime | None = Field(default=None, index=True)
    window_end: datetime | None = Field(default=None, index=True)
    input_count: int = Field(default=0, index=True)
    item_count: int = Field(default=0, index=True)
    inputs_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    items_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
