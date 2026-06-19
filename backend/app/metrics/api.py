"""Unregistered A08 Finance API router.

A09/A01 own central application registration. This module exports the A08 router so the
integration owner can mount it once shared auth/route contracts are accepted.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.metrics.brief_generation import (
    DailyBriefFromMetricRequest,
    UnavailableBriefSection,
    generate_daily_brief_detail_from_metric_snapshot,
)
from app.metrics.briefs import (
    DailyBriefItem,
    DailyBriefRequest,
    DailyBriefSection,
    DailyBriefSectionKind,
    ensure_daily_brief_delivery_intent,
    generate_daily_brief_snapshot,
    persist_daily_brief_snapshot,
    record_daily_brief_delivery_result,
    record_daily_brief_narration_result,
)
from app.metrics.formulas import FreshnessStatus, SourceCoverage
from app.metrics.read_models import (
    BriefCardSummary,
    DailyBriefDeliveryIntentRead,
    DailyBriefDeliveryPacket,
    DailyBriefDetail,
    MetricCardSummary,
    MetricExplainContext,
    MetricSnapshotDetail,
    build_metric_explain_context,
    get_brief_card_summary_by_id,
    get_daily_brief_delivery_packet,
    get_daily_brief_detail_by_id,
    get_latest_brief_card_summary,
    get_latest_daily_brief_detail,
    get_latest_metric_card_summary,
    get_metric_card_summary_by_id,
    get_metric_snapshot_detail,
    get_metric_snapshot_detail_by_id,
    list_daily_brief_delivery_intents,
)

router = APIRouter(prefix="/finance", tags=["finance"])

STORE_ID_QUERY = Query(..., min_length=1)
METRIC_NAME_QUERY = Query(default="estimated_contribution_margin", min_length=1)
CURRENCY_QUERY = Query(default=None, min_length=3, max_length=3)
REPORTING_TIMEZONE_QUERY = Query(default=None, min_length=1)
SESSION_DEP = Depends(get_session)


class DailyBriefItemIn(SQLModel):
    label: str
    value: str
    detail: str = ""
    evidence_refs: list[str] = []


class DailyBriefSectionIn(SQLModel):
    kind: DailyBriefSectionKind
    title: str
    coverage: SourceCoverage
    freshness: FreshnessStatus
    items: list[DailyBriefItemIn] = []
    warnings: list[str] = []
    evidence_refs: list[str] = []


class DailyBriefGenerateIn(SQLModel):
    brand_id: UUID
    store_id: str
    reporting_date: date
    reporting_timezone: str
    revision: int = 1
    sections: list[DailyBriefSectionIn] = []
    metric_snapshot_ids: list[str] = []
    generated_at: datetime | None = None
    trace_id: str | None = None


class UnavailableBriefSectionIn(SQLModel):
    kind: DailyBriefSectionKind
    reason: str
    evidence_refs: list[str] = []


class DailyBriefGenerateFromMetricIn(SQLModel):
    brand_id: UUID
    store_id: str
    reporting_date: date
    reporting_timezone: str
    metric_snapshot_id: str
    revision: int = 1
    unavailable_sections: list[UnavailableBriefSectionIn] = []
    generated_at: datetime | None = None
    trace_id: str | None = None


class DailyBriefDeliveryIntentIn(SQLModel):
    target_platform: str
    target_channel_ref: str
    trace_id: str | None = None


class DailyBriefNarrationResultIn(SQLModel):
    narration_status: str
    narrated_text: str | None = None
    hermes_session_id: str | None = None
    hermes_run_id: str | None = None
    hermes_cron_ref: str | None = None
    trace_id: str | None = None
    error: str | None = None


class DailyBriefDeliveryResultIn(SQLModel):
    status: str
    delivery_evidence: dict[str, object] = {}
    trace_id: str | None = None
    error: str | None = None
    delivered_at: datetime | None = None


@router.get("/metric-snapshots/latest", response_model=MetricSnapshotDetail)
async def latest_metric_snapshot(
    store_id: str = STORE_ID_QUERY,
    metric_name: str = METRIC_NAME_QUERY,
    currency: str | None = CURRENCY_QUERY,
    session: AsyncSession = SESSION_DEP,
) -> MetricSnapshotDetail:
    detail = await get_metric_snapshot_detail(
        session,
        store_id=store_id,
        metric_name=metric_name,
        currency=currency,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found",
        )
    return detail


@router.get("/metric-snapshots/latest/card", response_model=MetricCardSummary)
async def latest_metric_card(
    store_id: str = STORE_ID_QUERY,
    metric_name: str = METRIC_NAME_QUERY,
    currency: str | None = CURRENCY_QUERY,
    session: AsyncSession = SESSION_DEP,
) -> MetricCardSummary:
    summary = await get_latest_metric_card_summary(
        session,
        store_id=store_id,
        metric_name=metric_name,
        currency=currency,
    )
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found",
        )
    return summary


@router.get("/metric-snapshots/{snapshot_id}", response_model=MetricSnapshotDetail)
async def metric_snapshot_detail(
    snapshot_id: str,
    session: AsyncSession = SESSION_DEP,
) -> MetricSnapshotDetail:
    detail = await get_metric_snapshot_detail_by_id(session, snapshot_id=snapshot_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found",
        )
    return detail


@router.get("/metric-snapshots/{snapshot_id}/card", response_model=MetricCardSummary)
async def metric_card(
    snapshot_id: str,
    session: AsyncSession = SESSION_DEP,
) -> MetricCardSummary:
    try:
        summary = await get_metric_card_summary_by_id(session, snapshot_id=snapshot_id)
    except ValueError:
        summary = None
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found",
        )
    return summary


@router.get("/metric-snapshots/{snapshot_id}/explain-context", response_model=MetricExplainContext)
async def metric_snapshot_explain_context(
    snapshot_id: str,
    session: AsyncSession = SESSION_DEP,
) -> MetricExplainContext:
    context = await build_metric_explain_context(session, snapshot_id=snapshot_id)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found",
        )
    return context


@router.get("/daily-briefs/latest", response_model=DailyBriefDetail)
async def latest_daily_brief(
    store_id: str = STORE_ID_QUERY,
    reporting_date: date | None = Query(default=None),
    reporting_timezone: str | None = REPORTING_TIMEZONE_QUERY,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDetail:
    detail = await get_latest_daily_brief_detail(
        session,
        store_id=store_id,
        reporting_date=reporting_date,
        reporting_timezone=reporting_timezone,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    return detail


@router.get("/daily-briefs/{brief_id}", response_model=DailyBriefDetail)
async def daily_brief_detail(
    brief_id: str,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDetail:
    try:
        detail = await get_daily_brief_detail_by_id(session, brief_id=brief_id)
    except ValueError:
        detail = None
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    return detail


@router.get("/daily-briefs/latest/card", response_model=BriefCardSummary)
async def latest_daily_brief_card(
    store_id: str = STORE_ID_QUERY,
    reporting_date: date | None = Query(default=None),
    reporting_timezone: str | None = REPORTING_TIMEZONE_QUERY,
    session: AsyncSession = SESSION_DEP,
) -> BriefCardSummary:
    summary = await get_latest_brief_card_summary(
        session,
        store_id=store_id,
        reporting_date=reporting_date,
        reporting_timezone=reporting_timezone,
    )
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    return summary


@router.get("/daily-briefs/{brief_id}/card", response_model=BriefCardSummary)
async def daily_brief_card(
    brief_id: str,
    session: AsyncSession = SESSION_DEP,
) -> BriefCardSummary:
    try:
        summary = await get_brief_card_summary_by_id(session, brief_id=brief_id)
    except ValueError:
        summary = None
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    return summary


@router.post("/daily-briefs/generate", response_model=DailyBriefDetail)
async def generate_daily_brief(
    payload: DailyBriefGenerateIn,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDetail:
    snapshot = generate_daily_brief_snapshot(
        DailyBriefRequest(
            brand_id=str(payload.brand_id),
            store_id=payload.store_id,
            reporting_date=payload.reporting_date,
            reporting_timezone=payload.reporting_timezone,
            revision=payload.revision,
        ),
        sections=[
            DailyBriefSection(
                kind=section.kind,
                title=section.title,
                coverage=section.coverage,
                freshness=section.freshness,
                items=tuple(
                    DailyBriefItem(
                        label=item.label,
                        value=item.value,
                        detail=item.detail,
                        evidence_refs=tuple(item.evidence_refs),
                    )
                    for item in section.items
                ),
                warnings=tuple(section.warnings),
                evidence_refs=tuple(section.evidence_refs),
            )
            for section in payload.sections
        ],
        metric_snapshot_ids=payload.metric_snapshot_ids,
        generated_at=payload.generated_at,
        trace_id=payload.trace_id,
    )
    record = await persist_daily_brief_snapshot(
        session,
        brand_id=payload.brand_id,
        snapshot=snapshot,
    )
    detail = await get_daily_brief_detail_by_id(session, brief_id=str(record.id))
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="daily brief persisted but could not be read",
        )
    return detail


@router.post("/daily-briefs/generate-from-metric", response_model=DailyBriefDetail)
async def generate_daily_brief_from_metric(
    payload: DailyBriefGenerateFromMetricIn,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDetail:
    try:
        detail = await generate_daily_brief_detail_from_metric_snapshot(
            session,
            DailyBriefFromMetricRequest(
                brand_id=payload.brand_id,
                store_id=payload.store_id,
                reporting_date=payload.reporting_date,
                reporting_timezone=payload.reporting_timezone,
                metric_snapshot_id=payload.metric_snapshot_id,
                revision=payload.revision,
                unavailable_sections=tuple(
                    UnavailableBriefSection(
                        kind=section.kind,
                        reason=section.reason,
                        evidence_refs=tuple(section.evidence_refs),
                    )
                    for section in payload.unavailable_sections
                ),
                generated_at=payload.generated_at,
                trace_id=payload.trace_id,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="metric snapshot not found for daily brief scope",
        )
    return detail


@router.post("/daily-briefs/{brief_id}/narration-result", response_model=DailyBriefDetail)
async def record_daily_brief_narration_result_handler(
    brief_id: str,
    payload: DailyBriefNarrationResultIn,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDetail:
    try:
        record = await record_daily_brief_narration_result(
            session,
            brief_id=UUID(brief_id),
            narration_status=payload.narration_status,
            narrated_text=payload.narrated_text,
            hermes_session_id=payload.hermes_session_id,
            hermes_run_id=payload.hermes_run_id,
            hermes_cron_ref=payload.hermes_cron_ref,
            trace_id=payload.trace_id,
            error=payload.error,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    detail = await get_daily_brief_detail_by_id(session, brief_id=str(record.id))
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="daily brief updated but could not be read",
        )
    return detail


@router.get(
    "/daily-briefs/{brief_id}/delivery-intents",
    response_model=list[DailyBriefDeliveryIntentRead],
)
async def daily_brief_delivery_intents(
    brief_id: str,
    session: AsyncSession = SESSION_DEP,
) -> list[DailyBriefDeliveryIntentRead]:
    try:
        detail = await get_daily_brief_detail_by_id(session, brief_id=brief_id)
    except ValueError:
        detail = None
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    return await list_daily_brief_delivery_intents(session, brief_id=brief_id)


@router.post(
    "/daily-briefs/{brief_id}/delivery-intents",
    response_model=DailyBriefDeliveryIntentRead,
)
async def ensure_daily_brief_delivery_intent_handler(
    brief_id: str,
    payload: DailyBriefDeliveryIntentIn,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDeliveryIntentRead:
    try:
        detail = await get_daily_brief_detail_by_id(session, brief_id=brief_id)
    except ValueError:
        detail = None
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief not found",
        )
    intent = await ensure_daily_brief_delivery_intent(
        session,
        brief_id=UUID(brief_id),
        target_platform=payload.target_platform,
        target_channel_ref=payload.target_channel_ref,
        body_text=detail.final_text or detail.deterministic_fallback_text,
        trace_id=payload.trace_id,
    )
    intents = await list_daily_brief_delivery_intents(session, brief_id=brief_id)
    for read_intent in intents:
        if read_intent.id == str(intent.id):
            return read_intent
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="daily brief delivery intent persisted but could not be read",
    )


@router.post(
    "/daily-brief-delivery-intents/{intent_id}/result",
    response_model=DailyBriefDeliveryIntentRead,
)
async def record_daily_brief_delivery_result_handler(
    intent_id: str,
    payload: DailyBriefDeliveryResultIn,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDeliveryIntentRead:
    try:
        intent = await record_daily_brief_delivery_result(
            session,
            intent_id=UUID(intent_id),
            status=payload.status,
            delivery_evidence=payload.delivery_evidence,
            trace_id=payload.trace_id,
            error=payload.error,
            delivered_at=payload.delivered_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if intent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief delivery intent not found",
        )
    intents = await list_daily_brief_delivery_intents(session, brief_id=str(intent.brief_id))
    for read_intent in intents:
        if read_intent.id == str(intent.id):
            return read_intent
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="daily brief delivery intent updated but could not be read",
    )


@router.get(
    "/daily-brief-delivery-intents/{intent_id}/dispatch-packet",
    response_model=DailyBriefDeliveryPacket,
)
async def daily_brief_delivery_dispatch_packet(
    intent_id: str,
    session: AsyncSession = SESSION_DEP,
) -> DailyBriefDeliveryPacket:
    try:
        packet = await get_daily_brief_delivery_packet(session, intent_id=intent_id)
    except ValueError:
        packet = None
    if packet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="daily brief delivery intent not found",
        )
    return packet
