"""Trace, run, span, tool invocation, evidence, audit, and incident models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class Trace(QueryModel, table=True):
    """Top-level correlated operational activity."""

    __tablename__ = "traces"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        Index("ix_traces_entity", "primary_entity_type", "primary_entity_id"),
        Index("ix_traces_scope_started", "store_id", "started_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_type: str = Field(index=True)
    title: str
    summary: str | None = Field(default=None, sa_column=Column(Text))
    brand_id: UUID | None = Field(default=None, index=True)
    store_id: UUID | None = Field(default=None, index=True)
    root_actor_type: str
    root_actor_id: str
    root_event_id: UUID | None = Field(default=None, index=True)
    root_job_id: UUID | None = Field(default=None, index=True)
    root_request_id: str | None = Field(default=None, index=True)
    parent_trace_id: UUID | None = Field(default=None, index=True)
    primary_entity_type: str | None = Field(default=None, index=True)
    primary_entity_id: str | None = Field(default=None, index=True)
    status: str = Field(default="open", index=True)
    coverage: str = Field(default="unknown", index=True)
    retention_class: str = Field(default="trace_summary", index=True)
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = Field(default=None, index=True)
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class Run(QueryModel, table=True):
    """Hermes, deterministic, or human execution inside a trace."""

    __tablename__ = "runs"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_id: UUID = Field(foreign_key="traces.id", index=True)
    runtime: str = Field(index=True)
    status: str = Field(default="running", index=True)
    coverage: str = Field(default="unknown", index=True)
    hermes_profile_id: UUID | None = Field(default=None, index=True)
    hermes_session_id: str | None = Field(default=None, index=True)
    hermes_run_id: str | None = Field(default=None, index=True)
    source_platform: str | None = Field(default=None, index=True)
    model: str | None = None
    prompt_hash: str | None = Field(default=None, index=True)
    skill_hash: str | None = Field(default=None, index=True)
    config_hash: str | None = Field(default=None, index=True)
    end_reason: str | None = None
    cost_minor_units: int | None = None
    token_count: int | None = None
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = Field(default=None, index=True)
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class Span(QueryModel, table=True):
    """Timed operation in a trace timeline."""

    __tablename__ = "spans"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_spans_trace_started", "trace_id", "started_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_id: UUID = Field(foreign_key="traces.id", index=True)
    run_id: UUID | None = Field(default=None, foreign_key="runs.id", index=True)
    parent_span_id: UUID | None = Field(default=None, index=True)
    span_type: str = Field(index=True)
    name: str
    status: str = Field(default="open", index=True)
    coverage: str = Field(default="unknown", index=True)
    actor_type: str | None = None
    actor_id: str | None = None
    entity_type: str | None = Field(default=None, index=True)
    entity_id: str | None = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = Field(default=None, index=True)
    attributes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error_code: str | None = Field(default=None, index=True)
    error: str | None = Field(default=None, sa_column=Column(Text))


class ToolInvocation(QueryModel, table=True):
    """Durable request/result record for an Ecom-OS or observed Hermes tool call."""

    __tablename__ = "tool_invocations"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_tool_invocations_tool_started", "tool_name", "started_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_id: UUID = Field(foreign_key="traces.id", index=True)
    run_id: UUID | None = Field(default=None, foreign_key="runs.id", index=True)
    span_id: UUID | None = Field(default=None, foreign_key="spans.id", index=True)
    tool_name: str = Field(index=True)
    tool_version: str = Field(index=True)
    schema_hash: str = Field(index=True)
    transport: str = Field(index=True)
    actor_type: str
    actor_id: str
    effective_identity_type: str | None = None
    effective_identity_id: str | None = None
    store_id: UUID | None = Field(default=None, index=True)
    connection_id: UUID | None = Field(default=None, index=True)
    hermes_profile_id: UUID | None = Field(default=None, index=True)
    hermes_session_id: str | None = Field(default=None, index=True)
    hermes_run_id: str | None = Field(default=None, index=True)
    hermes_tool_call_id: str | None = Field(default=None, index=True)
    arguments_redacted: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_summary: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="started", index=True)
    coverage: str = Field(default="verified", index=True)
    error_code: str | None = Field(default=None, index=True)
    error: str | None = Field(default=None, sa_column=Column(Text))
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = Field(default=None, index=True)


class Evidence(QueryModel, table=True):
    """Source record, document excerpt, metric input, or observation used by work."""

    __tablename__ = "evidence"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_evidence_source_pair", "source", "source_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evidence_type: str = Field(index=True)
    source: str = Field(index=True)
    source_id: str = Field(index=True)
    source_timestamp: datetime | None = Field(default=None, index=True)
    collected_at: datetime = Field(default_factory=utcnow, index=True)
    trust_label: str = Field(default="untrusted", index=True)
    access_label: str = Field(default="internal", index=True)
    content_hash: str = Field(index=True)
    excerpt: str | None = Field(default=None, sa_column=Column(Text))
    reference: str | None = None
    superseded_by_id: UUID | None = Field(default=None, index=True)
    evidence_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class EvidenceLink(QueryModel, table=True):
    """Relationship between evidence and a trace/run/span/tool/action/incident."""

    __tablename__ = "evidence_links"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_evidence_links_target", "target_type", "target_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evidence_id: UUID = Field(foreign_key="evidence.id", index=True)
    target_type: str = Field(index=True)
    target_id: UUID = Field(index=True)
    purpose: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)


class AuditRecord(QueryModel, table=True):
    """Administrative or control-plane change record."""

    __tablename__ = "audit_records"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_id: UUID | None = Field(default=None, foreign_key="traces.id", index=True)
    actor_type: str = Field(index=True)
    actor_id: str = Field(index=True)
    action: str = Field(index=True)
    target_type: str | None = Field(default=None, index=True)
    target_id: str | None = Field(default=None, index=True)
    before: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    after: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    reason: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, index=True)


class Incident(QueryModel, table=True):
    """Operational investigation/remediation record."""

    __tablename__ = "incidents"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    severity: str = Field(default="medium", index=True)
    status: str = Field(default="open", index=True)
    owner_type: str | None = None
    owner_id: str | None = None
    detection_source: str | None = Field(default=None, index=True)
    root_trace_id: UUID | None = Field(default=None, foreign_key="traces.id", index=True)
    suspected_cause_category: str | None = Field(default=None, index=True)
    root_cause_confidence: str = Field(default="unknown", index=True)
    impact_summary: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    closed_at: datetime | None = None
    incident_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
