"""Response schemas for trace ledger and durable action activity endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import SQLModel

RUNTIME_ANNOTATION_TYPES = (datetime, UUID)


class TraceRead(SQLModel):
    """Serialized top-level trace summary."""

    id: UUID
    trace_type: str
    title: str
    summary: str | None
    brand_id: UUID | None
    store_id: UUID | None
    root_actor_type: str
    root_actor_id: str
    root_event_id: UUID | None
    root_job_id: UUID | None
    root_request_id: str | None
    parent_trace_id: UUID | None
    primary_entity_type: str | None
    primary_entity_id: str | None
    status: str
    coverage: str
    retention_class: str
    started_at: datetime
    ended_at: datetime | None
    attributes: dict[str, Any]


class RunRead(SQLModel):
    """Serialized execution run inside a trace."""

    id: UUID
    trace_id: UUID
    runtime: str
    status: str
    coverage: str
    hermes_profile_id: UUID | None
    hermes_session_id: str | None
    hermes_run_id: str | None
    source_platform: str | None
    model: str | None
    prompt_hash: str | None
    skill_hash: str | None
    config_hash: str | None
    end_reason: str | None
    cost_minor_units: int | None
    token_count: int | None
    started_at: datetime
    ended_at: datetime | None
    attributes: dict[str, Any]


class SpanRead(SQLModel):
    """Serialized trace span."""

    id: UUID
    trace_id: UUID
    run_id: UUID | None
    parent_span_id: UUID | None
    span_type: str
    name: str
    status: str
    coverage: str
    actor_type: str | None
    actor_id: str | None
    entity_type: str | None
    entity_id: str | None
    started_at: datetime
    ended_at: datetime | None
    attributes: dict[str, Any]
    error_code: str | None
    error: str | None


class ToolInvocationRead(SQLModel):
    """Serialized durable tool invocation record."""

    id: UUID
    trace_id: UUID
    run_id: UUID | None
    span_id: UUID | None
    tool_name: str
    tool_version: str
    schema_hash: str
    transport: str
    actor_type: str
    actor_id: str
    effective_identity_type: str | None
    effective_identity_id: str | None
    store_id: UUID | None
    connection_id: UUID | None
    hermes_profile_id: UUID | None
    hermes_session_id: str | None
    hermes_run_id: str | None
    hermes_tool_call_id: str | None
    arguments_redacted: dict[str, Any]
    result_summary: dict[str, Any] | None
    status: str
    coverage: str
    error_code: str | None
    error: str | None
    started_at: datetime
    ended_at: datetime | None


class EvidenceRead(SQLModel):
    """Serialized evidence item filtered for the caller's role."""

    id: UUID
    evidence_type: str
    source: str
    source_id: str
    source_timestamp: datetime | None
    collected_at: datetime
    trust_label: str
    access_label: str
    content_hash: str
    excerpt: str | None
    reference: str | None
    superseded_by_id: UUID | None
    evidence_metadata: dict[str, Any]


class ActionRead(SQLModel):
    """Serialized durable action intent summary."""

    id: UUID
    trace_id: UUID
    tool_invocation_id: UUID | None
    action_type: str
    schema_version: int
    store_id: UUID
    connection_id: UUID
    target_type: str
    target_id: str
    normalized_arguments: dict[str, Any]
    action_digest: str
    requested_actor_type: str
    requested_actor_id: str
    requested_run_id: UUID | None
    requested_session_id: str | None
    effective_grant: dict[str, Any]
    autonomy_mode: str
    policy_version: str | None
    policy_result: dict[str, Any] | None
    approval_required: bool
    approval_id: UUID | None
    intent_key: str
    state: str
    final_outcome_summary: dict[str, Any] | None
    reversibility: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ActionAttemptRead(SQLModel):
    """Serialized provider attempt for an action."""

    id: UUID
    action_id: UUID
    attempt_number: int
    connector: str
    connection_id: UUID
    provider_idempotency_key: str
    request_fingerprint: str
    safe_request_summary: dict[str, Any]
    provider_request_id: str | None
    provider_operation_id: str | None
    http_status_category: str | None
    safe_response_summary: dict[str, Any] | None
    retry_classification: str | None
    outcome_confidence: str
    error_reference: str | None
    reconciliation_due_at: datetime | None
    started_at: datetime
    ended_at: datetime | None


class ActionStateHistoryRead(SQLModel):
    """Serialized action state transition."""

    id: UUID
    action_id: UUID
    from_state: str | None
    to_state: str
    reason: str | None
    actor_type: str | None
    actor_id: str | None
    created_at: datetime
    transition_metadata: dict[str, Any]


class TraceDetailRead(SQLModel):
    """Trace detail with timeline records and role-filtered evidence."""

    trace: TraceRead
    runs: list[RunRead]
    spans: list[SpanRead]
    tool_invocations: list[ToolInvocationRead]
    actions: list[ActionRead]
    evidence: list[EvidenceRead]


class ActionDetailRead(SQLModel):
    """Action detail with provider attempts, state history, and filtered evidence."""

    action: ActionRead
    attempts: list[ActionAttemptRead]
    history: list[ActionStateHistoryRead]
    evidence: list[EvidenceRead]


class IncidentRead(SQLModel):
    """Serialized incident summary."""

    id: UUID
    title: str
    severity: str
    status: str
    owner_type: str | None
    owner_id: str | None
    detection_source: str | None
    root_trace_id: UUID | None
    suspected_cause_category: str | None
    root_cause_confidence: str
    impact_summary: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    incident_metadata: dict[str, Any]


class IncidentDetailRead(SQLModel):
    """Incident detail with root trace/action context and filtered evidence."""

    incident: IncidentRead
    root_trace: TraceRead | None = None
    related_actions: list[ActionRead]
    evidence: list[EvidenceRead]


class AuditRecordRead(SQLModel):
    """Serialized audit record for privileged operational review."""

    id: UUID
    trace_id: UUID | None
    actor_type: str
    actor_id: str
    action: str
    target_type: str | None
    target_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    created_at: datetime
