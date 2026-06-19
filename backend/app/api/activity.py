"""Activity listing and task-comment feed endpoints."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, asc, desc, func, or_
from sqlmodel import col, select
from sse_starlette.sse import EventSourceResponse

from app.api.deps import ActorContext, require_org_member, require_user_or_agent
from app.core.time import utcnow
from app.db.pagination import paginate
from app.db.session import async_session_maker, get_session
from app.models.actions import Action, ActionAttempt, ActionStateHistory
from app.models.activity_events import ActivityEvent
from app.models.agents import Agent
from app.models.boards import Board
from app.models.tasks import Task
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
from app.schemas.activity_events import (
    ActivityEventRead,
    ActivityTaskCommentFeedItemRead,
)
from app.schemas.pagination import DefaultLimitOffsetPage
from app.schemas.traces import (
    ActionAttemptRead,
    ActionDetailRead,
    ActionRead,
    ActionStateHistoryRead,
    AuditRecordRead,
    EvidenceRead,
    IncidentDetailRead,
    IncidentRead,
    RunRead,
    SpanRead,
    ToolInvocationRead,
    TraceDetailRead,
    TraceRead,
)
from app.services.organizations import (
    OrganizationContext,
    get_active_membership,
    list_accessible_board_ids,
)
from app.traces.recorder import ROLE_ACCESS

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from fastapi_pagination.limit_offset import LimitOffsetPage
    from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/activity", tags=["activity"])

SSE_SEEN_MAX = 2000
STREAM_POLL_SECONDS = 2
TASK_COMMENT_ROW_LEN = 4
SESSION_DEP = Depends(get_session)
ACTOR_DEP = Depends(require_user_or_agent)
ORG_MEMBER_DEP = Depends(require_org_member)
BOARD_ID_QUERY = Query(default=None)
SINCE_QUERY = Query(default=None)
_RUNTIME_TYPE_REFERENCES = (UUID,)
AUDIT_READ_ROLES = {"owner", "admin", "operator"}


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    normalized = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _agent_role(agent: Agent | None) -> str | None:
    if agent is None:
        return None
    profile = agent.identity_profile
    if not isinstance(profile, dict):
        return None
    raw = profile.get("role")
    if isinstance(raw, str):
        role = raw.strip()
        return role or None
    return None


async def _evidence_role_for_actor(session: AsyncSession, actor: ActorContext) -> str:
    """Resolve the caller to a trace-ledger evidence access role."""
    if actor.actor_type == "agent":
        agent_role = _agent_role(actor.agent)
        if agent_role in ROLE_ACCESS:
            return agent_role
        return "operator"
    if actor.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    member = await get_active_membership(session, actor.user)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    role = member.role.strip().lower()
    if role == "member":
        return "viewer"
    if role in ROLE_ACCESS:
        return role
    return "viewer"


async def _require_audit_read_role(session: AsyncSession, actor: ActorContext) -> str:
    role = await _evidence_role_for_actor(session, actor)
    if role not in AUDIT_READ_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return role


async def _list_evidence_for_targets(
    session: AsyncSession,
    *,
    role: str,
    targets: Sequence[tuple[str, UUID]],
) -> list[Evidence]:
    if not targets:
        return []
    allowed = ROLE_ACCESS.get(role, {"public"})
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
        .order_by(desc(col(Evidence.collected_at)))
    )
    evidence: list[Evidence] = []
    seen: set[UUID] = set()
    for item in (await session.exec(statement)).all():
        if item.id in seen:
            continue
        evidence.append(item)
        seen.add(item.id)
    return evidence


def _build_activity_route(
    *,
    event: ActivityEvent,
    board_id: UUID | None,
) -> tuple[str, dict[str, str]]:
    if board_id is not None:
        board_id_str = str(board_id)
        board_params = {"boardId": board_id_str}

        if event.event_type == "task.comment" and event.task_id is not None:
            return (
                "board",
                {
                    **board_params,
                    "taskId": str(event.task_id),
                    "commentId": str(event.id),
                },
            )

        if event.event_type.startswith("approval."):
            return ("board.approvals", board_params)

        if event.event_type.startswith("board."):
            return ("board", {**board_params, "panel": "chat"})

        if event.task_id is not None:
            return ("board", {**board_params, "taskId": str(event.task_id)})

        return ("board", board_params)

    fallback_params = {
        "eventId": str(event.id),
        "eventType": event.event_type,
        "createdAt": event.created_at.isoformat(),
    }
    if event.task_id is not None:
        fallback_params["taskId"] = str(event.task_id)
    return ("activity", fallback_params)


def _feed_item(
    event: ActivityEvent,
    task: Task,
    board: Board,
    agent: Agent | None,
) -> ActivityTaskCommentFeedItemRead:
    return ActivityTaskCommentFeedItemRead(
        id=event.id,
        created_at=event.created_at,
        message=event.message,
        agent_id=event.agent_id,
        agent_name=agent.name if agent else None,
        agent_role=_agent_role(agent),
        task_id=task.id,
        task_title=task.title,
        board_id=board.id,
        board_name=board.name,
    )


def _coerce_task_comment_rows(
    items: Sequence[Any],
) -> list[tuple[ActivityEvent, Task, Board, Agent | None]]:
    rows: list[tuple[ActivityEvent, Task, Board, Agent | None]] = []
    for item in items:
        first: Any
        second: Any
        third: Any
        fourth: Any

        if isinstance(item, tuple):
            if len(item) != TASK_COMMENT_ROW_LEN:
                msg = "Expected (ActivityEvent, Task, Board, Agent | None) rows"
                raise TypeError(msg)
            first, second, third, fourth = item
        else:
            try:
                row_len = len(item)
                first = item[0]
                second = item[1]
                third = item[2]
                fourth = item[3]
            except (IndexError, KeyError, TypeError):
                msg = "Expected (ActivityEvent, Task, Board, Agent | None) rows"
                raise TypeError(msg) from None
            if row_len != TASK_COMMENT_ROW_LEN:
                msg = "Expected (ActivityEvent, Task, Board, Agent | None) rows"
                raise TypeError(msg)

        if (
            isinstance(first, ActivityEvent)
            and isinstance(second, Task)
            and isinstance(third, Board)
            and (isinstance(fourth, Agent) or fourth is None)
        ):
            rows.append((first, second, third, fourth))
            continue

        msg = "Expected (ActivityEvent, Task, Board, Agent | None) rows"
        raise TypeError(msg)
    return rows


def _coerce_activity_rows(
    items: Sequence[Any],
) -> list[tuple[ActivityEvent, UUID | None, UUID | None]]:
    rows: list[tuple[ActivityEvent, UUID | None, UUID | None]] = []
    for item in items:
        first: Any
        second: Any
        third: Any

        if isinstance(item, tuple):
            if len(item) != 3:
                msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
                raise TypeError(msg)
            first, second, third = item
        else:
            try:
                row_len = len(item)
                first = item[0]
                second = item[1]
                third = item[2]
            except (IndexError, KeyError, TypeError):
                msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
                raise TypeError(msg) from None
            if row_len != 3:
                msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
                raise TypeError(msg)

        if not isinstance(first, ActivityEvent):
            msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
            raise TypeError(msg)
        if second is not None and not isinstance(second, UUID):
            msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
            raise TypeError(msg)
        if third is not None and not isinstance(third, UUID):
            msg = "Expected (ActivityEvent, event_board_id, task_board_id) rows"
            raise TypeError(msg)
        rows.append((first, second, third))
    return rows


async def _fetch_task_comment_events(
    session: AsyncSession,
    since: datetime,
    *,
    board_id: UUID | None = None,
) -> Sequence[tuple[ActivityEvent, Task, Board, Agent | None]]:
    statement = (
        select(ActivityEvent, Task, Board, Agent)
        .join(Task, col(ActivityEvent.task_id) == col(Task.id))
        .join(Board, col(Task.board_id) == col(Board.id))
        .outerjoin(Agent, col(ActivityEvent.agent_id) == col(Agent.id))
        .where(col(ActivityEvent.event_type) == "task.comment")
        .where(col(ActivityEvent.created_at) >= since)
        .where(func.length(func.trim(col(ActivityEvent.message))) > 0)
        .order_by(asc(col(ActivityEvent.created_at)))
    )
    if board_id is not None:
        statement = statement.where(col(Task.board_id) == board_id)
    return _coerce_task_comment_rows(list(await session.exec(statement)))


@router.get("", response_model=DefaultLimitOffsetPage[ActivityEventRead])
async def list_activity(
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[ActivityEventRead]:
    """List activity events visible to the calling actor."""
    statement: Any = select(
        ActivityEvent,
        col(ActivityEvent.board_id).label("event_board_id"),
        col(Task.board_id).label("task_board_id"),
    ).outerjoin(Task, col(ActivityEvent.task_id) == col(Task.id))
    if actor.actor_type == "agent" and actor.agent:
        statement = statement.where(col(ActivityEvent.agent_id) == actor.agent.id)
    elif actor.actor_type == "user" and actor.user:
        member = await get_active_membership(session, actor.user)
        if member is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        board_ids = await list_accessible_board_ids(session, member=member, write=False)
        if not board_ids:
            statement = statement.where(col(ActivityEvent.id).is_(None))
        else:
            statement = statement.where(
                or_(
                    col(ActivityEvent.board_id).in_(board_ids),
                    and_(
                        col(ActivityEvent.board_id).is_(None),
                        col(Task.board_id).in_(board_ids),
                    ),
                ),
            )
    statement = statement.order_by(desc(col(ActivityEvent.created_at)))

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        rows = _coerce_activity_rows(items)
        events: list[ActivityEventRead] = []
        for event, event_board_id, task_board_id in rows:
            payload = ActivityEventRead.model_validate(event, from_attributes=True)
            resolved_board_id = event_board_id or task_board_id
            payload.board_id = resolved_board_id
            route_name, route_params = _build_activity_route(
                event=event,
                board_id=resolved_board_id,
            )
            payload.route_name = route_name
            payload.route_params = route_params
            events.append(payload)
        return events

    return await paginate(session, statement, transformer=_transform)


@router.get("/traces", response_model=DefaultLimitOffsetPage[TraceRead])
async def list_traces(
    trace_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    coverage: str | None = Query(default=None),
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[TraceRead]:
    """List durable trace summaries visible to the calling actor."""
    await _evidence_role_for_actor(session, actor)
    if coverage is not None and coverage not in {
        "verified",
        "observed",
        "imported",
        "unknown",
    }:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    statement = select(Trace).order_by(desc(col(Trace.started_at)))
    if trace_type:
        statement = statement.where(Trace.trace_type == trace_type)
    if entity_type:
        statement = statement.where(Trace.primary_entity_type == entity_type)
    if entity_id:
        statement = statement.where(Trace.primary_entity_id == entity_id)
    if status_filter:
        statement = statement.where(Trace.status == status_filter)
    if coverage:
        statement = statement.where(Trace.coverage == coverage)

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        return [TraceRead.model_validate(item, from_attributes=True) for item in items]

    return await paginate(session, statement, transformer=_transform)


@router.get("/traces/{trace_id}", response_model=TraceDetailRead)
async def get_trace_detail(
    trace_id: UUID,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> TraceDetailRead:
    """Return a trace timeline with evidence filtered for the caller's role."""
    role = await _evidence_role_for_actor(session, actor)
    trace = await session.get(Trace, trace_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    runs = list(
        (
            await session.exec(
                select(Run).where(Run.trace_id == trace_id).order_by(asc(col(Run.started_at)))
            )
        ).all()
    )
    spans = list(
        (
            await session.exec(
                select(Span).where(Span.trace_id == trace_id).order_by(asc(col(Span.started_at)))
            )
        ).all()
    )
    tool_invocations = list(
        (
            await session.exec(
                select(ToolInvocation)
                .where(ToolInvocation.trace_id == trace_id)
                .order_by(asc(col(ToolInvocation.started_at)))
            )
        ).all()
    )
    actions = list(
        (
            await session.exec(
                select(Action)
                .where(Action.trace_id == trace_id)
                .order_by(asc(col(Action.created_at)))
            )
        ).all()
    )
    targets = [("trace", trace.id)]
    targets.extend(("run", item.id) for item in runs)
    targets.extend(("span", item.id) for item in spans)
    targets.extend(("tool_invocation", item.id) for item in tool_invocations)
    targets.extend(("action", item.id) for item in actions)
    evidence = await _list_evidence_for_targets(session, role=role, targets=targets)
    return TraceDetailRead(
        trace=TraceRead.model_validate(trace, from_attributes=True),
        runs=[RunRead.model_validate(item, from_attributes=True) for item in runs],
        spans=[SpanRead.model_validate(item, from_attributes=True) for item in spans],
        tool_invocations=[
            ToolInvocationRead.model_validate(item, from_attributes=True)
            for item in tool_invocations
        ],
        actions=[ActionRead.model_validate(item, from_attributes=True) for item in actions],
        evidence=[EvidenceRead.model_validate(item, from_attributes=True) for item in evidence],
    )


@router.get("/actions", response_model=DefaultLimitOffsetPage[ActionRead])
async def list_actions(
    trace_id: UUID | None = Query(default=None),
    state: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[ActionRead]:
    """List durable external-write action intents."""
    await _evidence_role_for_actor(session, actor)
    statement = select(Action).order_by(desc(col(Action.created_at)))
    if trace_id is not None:
        statement = statement.where(Action.trace_id == trace_id)
    if state:
        statement = statement.where(Action.state == state)
    if action_type:
        statement = statement.where(Action.action_type == action_type)
    if target_type:
        statement = statement.where(Action.target_type == target_type)
    if target_id:
        statement = statement.where(Action.target_id == target_id)

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        return [ActionRead.model_validate(item, from_attributes=True) for item in items]

    return await paginate(session, statement, transformer=_transform)


@router.get("/actions/{action_id}", response_model=ActionDetailRead)
async def get_action_detail(
    action_id: UUID,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> ActionDetailRead:
    """Return durable action state, attempts, history, and filtered evidence."""
    role = await _evidence_role_for_actor(session, actor)
    action = await session.get(Action, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    attempts = list(
        (
            await session.exec(
                select(ActionAttempt)
                .where(ActionAttempt.action_id == action_id)
                .order_by(asc(col(ActionAttempt.attempt_number)))
            )
        ).all()
    )
    history = list(
        (
            await session.exec(
                select(ActionStateHistory)
                .where(ActionStateHistory.action_id == action_id)
                .order_by(asc(col(ActionStateHistory.created_at)))
            )
        ).all()
    )
    evidence = await _list_evidence_for_targets(
        session,
        role=role,
        targets=[("action", action.id)],
    )
    return ActionDetailRead(
        action=ActionRead.model_validate(action, from_attributes=True),
        attempts=[
            ActionAttemptRead.model_validate(item, from_attributes=True) for item in attempts
        ],
        history=[
            ActionStateHistoryRead.model_validate(item, from_attributes=True) for item in history
        ],
        evidence=[EvidenceRead.model_validate(item, from_attributes=True) for item in evidence],
    )


@router.get("/incidents", response_model=DefaultLimitOffsetPage[IncidentRead])
async def list_incidents(
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    detection_source: str | None = Query(default=None),
    root_trace_id: UUID | None = Query(default=None),
    suspected_cause_category: str | None = Query(default=None),
    root_cause_confidence: str | None = Query(default=None),
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[IncidentRead]:
    """List incident summaries for operational diagnosis."""
    await _evidence_role_for_actor(session, actor)
    statement = select(Incident).order_by(desc(col(Incident.created_at)))
    if severity:
        statement = statement.where(Incident.severity == severity)
    if status_filter:
        statement = statement.where(Incident.status == status_filter)
    if detection_source:
        statement = statement.where(Incident.detection_source == detection_source)
    if root_trace_id is not None:
        statement = statement.where(Incident.root_trace_id == root_trace_id)
    if suspected_cause_category:
        statement = statement.where(Incident.suspected_cause_category == suspected_cause_category)
    if root_cause_confidence:
        statement = statement.where(Incident.root_cause_confidence == root_cause_confidence)

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        return [IncidentRead.model_validate(item, from_attributes=True) for item in items]

    return await paginate(session, statement, transformer=_transform)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailRead)
async def get_incident_detail(
    incident_id: UUID,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> IncidentDetailRead:
    """Return an incident with trace/action context and filtered evidence."""
    role = await _evidence_role_for_actor(session, actor)
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    root_trace = (
        await session.get(Trace, incident.root_trace_id)
        if incident.root_trace_id is not None
        else None
    )
    related_actions: list[Action] = []
    targets = [("incident", incident.id)]
    if root_trace is not None:
        related_actions = list(
            (
                await session.exec(
                    select(Action)
                    .where(Action.trace_id == root_trace.id)
                    .order_by(asc(col(Action.created_at)))
                )
            ).all()
        )
        targets.append(("trace", root_trace.id))
        targets.extend(("action", item.id) for item in related_actions)
    evidence = await _list_evidence_for_targets(session, role=role, targets=targets)
    return IncidentDetailRead(
        incident=IncidentRead.model_validate(incident, from_attributes=True),
        root_trace=(
            TraceRead.model_validate(root_trace, from_attributes=True)
            if root_trace is not None
            else None
        ),
        related_actions=[
            ActionRead.model_validate(item, from_attributes=True) for item in related_actions
        ],
        evidence=[EvidenceRead.model_validate(item, from_attributes=True) for item in evidence],
    )


@router.get("/audit", response_model=DefaultLimitOffsetPage[AuditRecordRead])
async def list_audit_records(
    action: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    trace_id: UUID | None = Query(default=None),
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> LimitOffsetPage[AuditRecordRead]:
    """List privileged audit records for operational review."""
    await _require_audit_read_role(session, actor)
    statement = select(AuditRecord).order_by(desc(col(AuditRecord.created_at)))
    if action:
        statement = statement.where(AuditRecord.action == action)
    if actor_type:
        statement = statement.where(AuditRecord.actor_type == actor_type)
    if actor_id:
        statement = statement.where(AuditRecord.actor_id == actor_id)
    if target_type:
        statement = statement.where(AuditRecord.target_type == target_type)
    if target_id:
        statement = statement.where(AuditRecord.target_id == target_id)
    if trace_id is not None:
        statement = statement.where(AuditRecord.trace_id == trace_id)

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        return [AuditRecordRead.model_validate(item, from_attributes=True) for item in items]

    return await paginate(session, statement, transformer=_transform)


@router.get("/audit/{audit_id}", response_model=AuditRecordRead)
async def get_audit_record(
    audit_id: UUID,
    session: AsyncSession = SESSION_DEP,
    actor: ActorContext = ACTOR_DEP,
) -> AuditRecordRead:
    """Return one privileged audit record."""
    await _require_audit_read_role(session, actor)
    audit = await session.get(AuditRecord, audit_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AuditRecordRead.model_validate(audit, from_attributes=True)


@router.get(
    "/task-comments",
    response_model=DefaultLimitOffsetPage[ActivityTaskCommentFeedItemRead],
)
async def list_task_comment_feed(
    board_id: UUID | None = BOARD_ID_QUERY,
    session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> LimitOffsetPage[ActivityTaskCommentFeedItemRead]:
    """List task-comment feed items for accessible boards."""
    statement = (
        select(ActivityEvent, Task, Board, Agent)
        .join(Task, col(ActivityEvent.task_id) == col(Task.id))
        .join(Board, col(Task.board_id) == col(Board.id))
        .outerjoin(Agent, col(ActivityEvent.agent_id) == col(Agent.id))
        .where(col(ActivityEvent.event_type) == "task.comment")
        .where(func.length(func.trim(col(ActivityEvent.message))) > 0)
        .order_by(desc(col(ActivityEvent.created_at)))
    )
    board_ids = await list_accessible_board_ids(session, member=ctx.member, write=False)
    if board_id is not None:
        if board_id not in set(board_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        statement = statement.where(col(Task.board_id) == board_id)
    elif board_ids:
        statement = statement.where(col(Task.board_id).in_(board_ids))
    else:
        statement = statement.where(col(Task.id).is_(None))

    def _transform(items: Sequence[Any]) -> Sequence[Any]:
        rows = _coerce_task_comment_rows(items)
        return [_feed_item(event, task, board, agent) for event, task, board, agent in rows]

    return await paginate(session, statement, transformer=_transform)


@router.get("/task-comments/stream")
async def stream_task_comment_feed(
    request: Request,
    board_id: UUID | None = BOARD_ID_QUERY,
    since: str | None = SINCE_QUERY,
    db_session: AsyncSession = SESSION_DEP,
    ctx: OrganizationContext = ORG_MEMBER_DEP,
) -> EventSourceResponse:
    """Stream task-comment events for accessible boards."""
    since_dt = _parse_since(since) or utcnow()
    board_ids = await list_accessible_board_ids(
        db_session,
        member=ctx.member,
        write=False,
    )
    allowed_ids = set(board_ids)
    if board_id is not None and board_id not in allowed_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    seen_ids: set[UUID] = set()
    seen_queue: deque[UUID] = deque()

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        last_seen = since_dt
        while True:
            if await request.is_disconnected():
                break
            async with async_session_maker() as stream_session:
                if board_id is not None:
                    rows = await _fetch_task_comment_events(
                        stream_session,
                        last_seen,
                        board_id=board_id,
                    )
                elif allowed_ids:
                    rows = await _fetch_task_comment_events(stream_session, last_seen)
                    rows = [row for row in rows if row[1].board_id in allowed_ids]
                else:
                    rows = []
            for event, task, board, agent in rows:
                event_id = event.id
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)
                seen_queue.append(event_id)
                if len(seen_queue) > SSE_SEEN_MAX:
                    oldest = seen_queue.popleft()
                    seen_ids.discard(oldest)
                last_seen = max(event.created_at, last_seen)
                payload = {
                    "comment": _feed_item(
                        event,
                        task,
                        board,
                        agent,
                    ).model_dump(mode="json"),
                }
                yield {"event": "comment", "data": json.dumps(payload)}
            await asyncio.sleep(STREAM_POLL_SECONDS)

    return EventSourceResponse(event_generator(), ping=15)
