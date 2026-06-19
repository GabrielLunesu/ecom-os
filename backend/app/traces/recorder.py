"""Trace recorder, tool invocation recorder, evidence store, and incident helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.traces import (
    AuditRecord,
    Evidence,
    EvidenceLink,
    Incident,
    Run,
    Span,
    ToolInvocation,
    Trace,
)

VALID_COVERAGE = {"verified", "observed", "imported", "unknown"}
SECRET_LABELS = {"secret", "credential", "secret/credential"}
SECRET_FIELD_KEYS = {
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}
ROLE_ACCESS: dict[str, set[str]] = {
    "owner": {
        "public",
        "internal",
        "customer_pii",
        "employee_private",
        "financial_sensitive",
    },
    "admin": {"public", "internal", "customer_pii", "employee_private"},
    "operator": {"public", "internal", "customer_pii"},
    "cs_lead": {"public", "internal", "customer_pii"},
    "cs_rep": {"public", "internal", "customer_pii"},
    "finance": {"public", "internal", "financial_sensitive"},
    "viewer": {"public", "internal"},
}


def _assert_coverage(coverage: str) -> None:
    if coverage not in VALID_COVERAGE:
        raise ValueError(f"unsupported coverage={coverage!r}")


def content_hash(value: str | dict[str, Any]) -> str:
    if isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _contains_secret_field_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in SECRET_FIELD_KEYS:
                return True
            if _contains_secret_field_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_field_key(item) for item in value)
    return False


async def create_trace(
    session: AsyncSession,
    *,
    trace_type: str,
    title: str,
    root_actor_type: str,
    root_actor_id: str,
    brand_id: UUID | None = None,
    store_id: UUID | None = None,
    root_event_id: UUID | None = None,
    root_job_id: UUID | None = None,
    root_request_id: str | None = None,
    parent_trace_id: UUID | None = None,
    primary_entity_type: str | None = None,
    primary_entity_id: str | None = None,
    coverage: str = "unknown",
    attributes: dict[str, Any] | None = None,
) -> Trace:
    _assert_coverage(coverage)
    trace = Trace(
        trace_type=trace_type,
        title=title,
        root_actor_type=root_actor_type,
        root_actor_id=root_actor_id,
        brand_id=brand_id,
        store_id=store_id,
        root_event_id=root_event_id,
        root_job_id=root_job_id,
        root_request_id=root_request_id,
        parent_trace_id=parent_trace_id,
        primary_entity_type=primary_entity_type,
        primary_entity_id=primary_entity_id,
        coverage=coverage,
        attributes=attributes or {},
    )
    session.add(trace)
    await session.flush()
    return trace


async def create_run(
    session: AsyncSession,
    *,
    trace_id: UUID,
    runtime: str,
    coverage: str,
    hermes_session_id: str | None = None,
    hermes_run_id: str | None = None,
    model: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Run:
    _assert_coverage(coverage)
    run = Run(
        trace_id=trace_id,
        runtime=runtime,
        coverage=coverage,
        hermes_session_id=hermes_session_id,
        hermes_run_id=hermes_run_id,
        model=model,
        attributes=attributes or {},
    )
    session.add(run)
    await session.flush()
    return run


async def create_span(
    session: AsyncSession,
    *,
    trace_id: UUID,
    span_type: str,
    name: str,
    coverage: str,
    run_id: UUID | None = None,
    parent_span_id: UUID | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Span:
    _assert_coverage(coverage)
    span = Span(
        trace_id=trace_id,
        run_id=run_id,
        parent_span_id=parent_span_id,
        span_type=span_type,
        name=name,
        coverage=coverage,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        attributes=attributes or {},
    )
    session.add(span)
    await session.flush()
    return span


async def complete_span(
    session: AsyncSession,
    span: Span,
    *,
    status: str = "succeeded",
    error_code: str | None = None,
    error: str | None = None,
) -> Span:
    span.status = status
    span.ended_at = utcnow()
    span.error_code = error_code
    span.error = error
    session.add(span)
    await session.flush()
    return span


async def record_tool_invocation(
    session: AsyncSession,
    *,
    trace_id: UUID,
    tool_name: str,
    tool_version: str,
    schema_hash: str,
    transport: str,
    actor_type: str,
    actor_id: str,
    arguments_redacted: dict[str, Any],
    run_id: UUID | None = None,
    span_id: UUID | None = None,
    store_id: UUID | None = None,
    connection_id: UUID | None = None,
    coverage: str = "verified",
    hermes_session_id: str | None = None,
    hermes_run_id: str | None = None,
    hermes_tool_call_id: str | None = None,
) -> ToolInvocation:
    _assert_coverage(coverage)
    if _contains_secret_field_key(arguments_redacted):
        raise ValueError("tool invocation arguments must be redacted before recording")
    invocation = ToolInvocation(
        trace_id=trace_id,
        run_id=run_id,
        span_id=span_id,
        tool_name=tool_name,
        tool_version=tool_version,
        schema_hash=schema_hash,
        transport=transport,
        actor_type=actor_type,
        actor_id=actor_id,
        store_id=store_id,
        connection_id=connection_id,
        arguments_redacted=arguments_redacted,
        coverage=coverage,
        hermes_session_id=hermes_session_id,
        hermes_run_id=hermes_run_id,
        hermes_tool_call_id=hermes_tool_call_id,
    )
    session.add(invocation)
    await session.flush()
    return invocation


async def finish_tool_invocation(
    session: AsyncSession,
    invocation: ToolInvocation,
    *,
    status: str,
    result_summary: dict[str, Any] | None = None,
    error_code: str | None = None,
    error: str | None = None,
) -> ToolInvocation:
    if _contains_secret_field_key(result_summary):
        raise ValueError("tool invocation results must be redacted before recording")
    invocation.status = status
    invocation.result_summary = result_summary
    invocation.error_code = error_code
    invocation.error = error
    invocation.ended_at = utcnow()
    session.add(invocation)
    await session.flush()
    return invocation


async def add_evidence(
    session: AsyncSession,
    *,
    evidence_type: str,
    source: str,
    source_id: str,
    trust_label: str,
    access_label: str,
    excerpt: str | None = None,
    reference: str | None = None,
    source_timestamp: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Evidence:
    if access_label in SECRET_LABELS:
        raise ValueError("secret evidence must not be stored in the trace ledger")
    if _contains_secret_field_key(metadata):
        raise ValueError("evidence metadata must not store secret-bearing fields")
    hashed = content_hash(excerpt or reference or metadata or source_id)
    evidence = Evidence(
        evidence_type=evidence_type,
        source=source,
        source_id=source_id,
        source_timestamp=source_timestamp,
        trust_label=trust_label,
        access_label=access_label,
        content_hash=hashed,
        excerpt=excerpt,
        reference=reference,
        evidence_metadata=metadata or {},
    )
    session.add(evidence)
    await session.flush()
    return evidence


async def link_evidence(
    session: AsyncSession,
    *,
    evidence_id: UUID,
    target_type: str,
    target_id: UUID,
    purpose: str,
) -> EvidenceLink:
    link = EvidenceLink(
        evidence_id=evidence_id,
        target_type=target_type,
        target_id=target_id,
        purpose=purpose,
    )
    session.add(link)
    await session.flush()
    return link


async def list_evidence_for_role(
    session: AsyncSession,
    *,
    role: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
) -> Sequence[Evidence]:
    allowed = ROLE_ACCESS.get(role, {"public"})
    statement = select(Evidence).where(col(Evidence.access_label).in_(allowed))
    if target_type and target_id:
        statement = statement.join(
            EvidenceLink,
            col(EvidenceLink.evidence_id) == col(Evidence.id),
        ).where(
            EvidenceLink.target_type == target_type,
            EvidenceLink.target_id == target_id,
        )
    return list((await session.exec(statement)).all())


async def search_traces(
    session: AsyncSession,
    *,
    trace_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    status: str | None = None,
    coverage: str | None = None,
) -> Sequence[Trace]:
    statement = select(Trace).order_by(col(Trace.started_at).desc())
    if trace_type:
        statement = statement.where(Trace.trace_type == trace_type)
    if entity_type:
        statement = statement.where(Trace.primary_entity_type == entity_type)
    if entity_id:
        statement = statement.where(Trace.primary_entity_id == entity_id)
    if status:
        statement = statement.where(Trace.status == status)
    if coverage:
        _assert_coverage(coverage)
        statement = statement.where(Trace.coverage == coverage)
    return list((await session.exec(statement)).all())


async def record_audit(
    session: AsyncSession,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    trace_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditRecord:
    if _contains_secret_field_key(before) or _contains_secret_field_key(after):
        raise ValueError("audit records must not store secret-bearing fields")
    audit = AuditRecord(
        trace_id=trace_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        reason=reason,
    )
    session.add(audit)
    await session.flush()
    return audit


async def create_incident(
    session: AsyncSession,
    *,
    title: str,
    severity: str,
    detection_source: str,
    root_trace_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> Incident:
    incident = Incident(
        title=title,
        severity=severity,
        detection_source=detection_source,
        root_trace_id=root_trace_id,
        incident_metadata=metadata or {},
    )
    session.add(incident)
    await session.flush()
    return incident
