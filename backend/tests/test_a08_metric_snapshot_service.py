from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
)
from app.metrics.models import MetricComponentRecord
from app.metrics.snapshots import (
    ContributionComponentSource,
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
    persist_metric_snapshot,
)
from app.models.brand import Brand


class _FakeSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        assert request.store_id == "store_1"
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=20_000, currency=request.currency),
                source_ref="orders",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:orders"],
            ),
            MetricComponentInput(
                kind=ComponentKind.COGS,
                amount=Money(minor=8_000, currency=request.currency),
                source_ref="costs",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:costs"],
            ),
        ]


@pytest.mark.asyncio
async def test_snapshot_service_generates_formula_snapshot_from_source_port() -> None:
    request = MetricSnapshotRequest(
        brand_id="brand_1",
        store_id="store_1",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )

    snapshot = await generate_estimated_contribution_margin_snapshot(
        request,
        source=_FakeSource(),
    )

    assert snapshot.metric_name == "estimated_contribution_margin"
    assert snapshot.store_id == "store_1"
    assert snapshot.value == Money(minor=12_000, currency="USD")
    assert snapshot.window.local_date == date(2026, 6, 17)
    assert snapshot.coverage == SourceCoverage.PARTIAL
    assert ComponentKind.ATTRIBUTED_AD_SPEND in snapshot.missing_component_kinds


@pytest.mark.asyncio
async def test_persist_metric_snapshot_is_idempotent_by_window_formula_currency() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Test Brand")
        session.add(brand)
        await session.flush()
        request = MetricSnapshotRequest(
            brand_id=str(brand.id),
            store_id="store_1",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
            currency="USD",
            attribution_window_days=7,
            fx_basis="provider_daily_close",
        )
        snapshot = await generate_estimated_contribution_margin_snapshot(
            request,
            source=_FakeSource(),
        )

        first = await persist_metric_snapshot(
            session,
            brand_id=brand.id,
            snapshot=snapshot,
            trace_id="trace_123",
        )
        second = await persist_metric_snapshot(
            session,
            brand_id=brand.id,
            snapshot=snapshot,
            trace_id="trace_456",
        )

        component_count = (
            await session.exec(select(func.count()).select_from(MetricComponentRecord))
        ).one()

    assert first.id == second.id
    assert first.trace_id == "trace_123"
    assert component_count == len(snapshot.components)
