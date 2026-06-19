"""Metric snapshot generation and persistence services for A08."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.formulas import (
    MetricComponentInput,
    MetricSnapshot,
    calculate_estimated_contribution_margin,
    reporting_window_for_local_day,
)
from app.metrics.models import MetricComponentRecord, MetricSnapshotRecord


@dataclass(frozen=True, slots=True)
class MetricSnapshotRequest:
    brand_id: str
    store_id: str
    reporting_date: date
    reporting_timezone: str
    currency: str
    attribution_window_days: int
    fx_basis: str


class ContributionComponentSource(Protocol):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]: ...


async def generate_estimated_contribution_margin_snapshot(
    request: MetricSnapshotRequest,
    *,
    source: ContributionComponentSource,
) -> MetricSnapshot:
    components = await source.components_for_estimated_contribution_margin(request)
    return calculate_estimated_contribution_margin(
        store_id=request.store_id,
        window=reporting_window_for_local_day(
            request.reporting_date,
            request.reporting_timezone,
        ),
        currency=request.currency,
        components=components,
        attribution_window_days=request.attribution_window_days,
        fx_basis=request.fx_basis,
    )


async def persist_metric_snapshot(
    session: AsyncSession,
    *,
    brand_id: UUID,
    snapshot: MetricSnapshot,
    trace_id: str | None = None,
) -> MetricSnapshotRecord:
    existing = (
        await session.exec(
            select(MetricSnapshotRecord)
            .where(col(MetricSnapshotRecord.store_id) == snapshot.store_id)
            .where(col(MetricSnapshotRecord.metric_name) == snapshot.metric_name)
            .where(col(MetricSnapshotRecord.formula_version) == snapshot.formula_version)
            .where(col(MetricSnapshotRecord.window_start_at) == snapshot.window.start_utc)
            .where(col(MetricSnapshotRecord.window_end_at) == snapshot.window.end_utc)
            .where(col(MetricSnapshotRecord.currency) == snapshot.currency),
        )
    ).first()
    if existing is not None:
        return existing

    record = MetricSnapshotRecord.from_domain(
        brand_id=brand_id,
        snapshot=snapshot,
        trace_id=trace_id,
    )
    session.add(record)
    await session.flush()
    for component in snapshot.components:
        session.add(
            MetricComponentRecord.from_domain(
                snapshot_id=record.id,
                component=component,
            )
        )
    await session.commit()
    await session.refresh(record)
    return record
