"""Typed trace-search tool contracts for downstream agents and UI surfaces."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlmodel import SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.actions import Action
from app.models.traces import Evidence, EvidenceLink, Run, Span, ToolInvocation
from app.schemas.traces import EvidenceRead, TraceRead
from app.traces.recorder import ROLE_ACCESS, search_traces

MAX_TRACE_SEARCH_LIMIT = 100


class TraceSearchToolInput(SQLModel):
    """Typed, read-only trace search request for agent-facing tooling."""

    role: str = "viewer"
    trace_type: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    status: str | None = None
    coverage: str | None = None
    include_evidence: bool = True
    limit: int = 20


class TraceSearchToolItem(SQLModel):
    """One trace search result with evidence already filtered by role."""

    trace: TraceRead
    evidence: list[EvidenceRead]


class TraceSearchToolResult(SQLModel):
    """Trace search tool output safe to send to an agent/model context."""

    role: str
    filters: dict[str, Any]
    results: list[TraceSearchToolItem]


async def _trace_evidence_targets(
    session: AsyncSession,
    trace_id: UUID,
) -> list[tuple[str, UUID]]:
    targets: list[tuple[str, UUID]] = [("trace", trace_id)]
    runs = list((await session.exec(select(Run.id).where(Run.trace_id == trace_id))).all())
    spans = list((await session.exec(select(Span.id).where(Span.trace_id == trace_id))).all())
    invocations = list(
        (
            await session.exec(select(ToolInvocation.id).where(ToolInvocation.trace_id == trace_id))
        ).all()
    )
    actions = list((await session.exec(select(Action.id).where(Action.trace_id == trace_id))).all())
    targets.extend(("run", item) for item in runs)
    targets.extend(("span", item) for item in spans)
    targets.extend(("tool_invocation", item) for item in invocations)
    targets.extend(("action", item) for item in actions)
    return targets


async def _role_filtered_trace_evidence(
    session: AsyncSession,
    *,
    role: str,
    trace_id: UUID,
) -> list[EvidenceRead]:
    allowed = ROLE_ACCESS.get(role, {"public"})
    targets = await _trace_evidence_targets(session, trace_id)
    target_filters = [
        and_(
            col(EvidenceLink.target_type) == target_type,
            col(EvidenceLink.target_id) == target_id,
        )
        for target_type, target_id in targets
    ]
    statement = (
        select(Evidence)
        .join(EvidenceLink, col(EvidenceLink.evidence_id) == col(Evidence.id))
        .where(col(Evidence.access_label).in_(allowed))
        .where(or_(*target_filters))
        .order_by(col(Evidence.collected_at).desc())
    )
    evidence: list[EvidenceRead] = []
    seen: set[UUID] = set()
    for item in (await session.exec(statement)).all():
        if item.id in seen:
            continue
        seen.add(item.id)
        evidence.append(EvidenceRead.model_validate(item, from_attributes=True))
    return evidence


async def trace_search_tool(
    session: AsyncSession,
    request: TraceSearchToolInput,
) -> TraceSearchToolResult:
    """Run trace search and filter evidence before returning tool output."""

    if request.limit < 1 or request.limit > MAX_TRACE_SEARCH_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_TRACE_SEARCH_LIMIT}")
    traces = list(
        await search_traces(
            session,
            trace_type=request.trace_type,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            status=request.status,
            coverage=request.coverage,
        )
    )[: request.limit]
    results: list[TraceSearchToolItem] = []
    for trace in traces:
        evidence = (
            await _role_filtered_trace_evidence(
                session,
                role=request.role,
                trace_id=trace.id,
            )
            if request.include_evidence
            else []
        )
        results.append(
            TraceSearchToolItem(
                trace=TraceRead.model_validate(trace, from_attributes=True),
                evidence=evidence,
            )
        )
    return TraceSearchToolResult(
        role=request.role,
        filters={
            "trace_type": request.trace_type,
            "entity_type": request.entity_type,
            "entity_id": request.entity_id,
            "status": request.status,
            "coverage": request.coverage,
            "include_evidence": request.include_evidence,
            "limit": request.limit,
        },
        results=results,
    )
