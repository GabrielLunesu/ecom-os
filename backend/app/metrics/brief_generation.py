"""A08 daily brief generation service from persisted metric evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import cast
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.brief_composer import (
    MetricSnapshotForBrief,
    compose_daily_brief_snapshot,
    unavailable_operational_section,
)
from app.metrics.briefs import DailyBriefRequest, DailyBriefSection, DailyBriefSectionKind
from app.metrics.models import DailyBriefRecord
from app.metrics.read_models import (
    DailyBriefDetail,
    MetricSnapshotDetail,
    get_daily_brief_detail_by_id,
    get_metric_snapshot_detail_by_id,
)


@dataclass(frozen=True, slots=True)
class UnavailableBriefSection:
    kind: DailyBriefSectionKind
    reason: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DailyBriefFromMetricRequest:
    brand_id: UUID
    store_id: str
    reporting_date: date
    reporting_timezone: str
    metric_snapshot_id: str
    revision: int = 1
    unavailable_sections: tuple[UnavailableBriefSection, ...] = ()
    generated_at: datetime | None = None
    trace_id: str | None = None


async def generate_daily_brief_from_metric_snapshot(
    session: AsyncSession,
    request: DailyBriefFromMetricRequest,
) -> DailyBriefRecord | None:
    """Generate or retrieve a daily brief from one exact metric snapshot.

    Returning `None` means the snapshot is missing or does not match the exact
    store/date/timezone scope. The caller decides whether that is a 404 or invalid
    argument response.
    """

    metric = await get_metric_snapshot_detail_by_id(
        session,
        snapshot_id=request.metric_snapshot_id,
    )
    if metric is None or not _matches_scope(metric, request):
        return None

    sections = _sections_from_unavailable_inputs(request.unavailable_sections)
    snapshot = compose_daily_brief_snapshot(
        DailyBriefRequest(
            brand_id=str(request.brand_id),
            store_id=request.store_id,
            reporting_date=request.reporting_date,
            reporting_timezone=request.reporting_timezone,
            revision=request.revision,
        ),
        metric_snapshot=cast(MetricSnapshotForBrief, metric),
        sections=sections,
        generated_at=request.generated_at,
        trace_id=request.trace_id,
    )

    from app.metrics.briefs import persist_daily_brief_snapshot

    return await persist_daily_brief_snapshot(
        session,
        brand_id=request.brand_id,
        snapshot=snapshot,
    )


async def generate_daily_brief_detail_from_metric_snapshot(
    session: AsyncSession,
    request: DailyBriefFromMetricRequest,
) -> DailyBriefDetail | None:
    record = await generate_daily_brief_from_metric_snapshot(session, request)
    if record is None:
        return None
    return await get_daily_brief_detail_by_id(session, brief_id=str(record.id))


def _matches_scope(
    metric: MetricSnapshotDetail,
    request: DailyBriefFromMetricRequest,
) -> bool:
    return (
        metric.store_id == request.store_id
        and metric.window.reporting_date == request.reporting_date
        and metric.window.timezone == request.reporting_timezone
    )


def _sections_from_unavailable_inputs(
    unavailable_sections: tuple[UnavailableBriefSection, ...],
) -> list[DailyBriefSection]:
    return [
        unavailable_operational_section(
            section.kind,
            reason=section.reason,
            evidence_refs=section.evidence_refs,
        )
        for section in unavailable_sections
    ]
