from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.brief_generation import (
    DailyBriefFromMetricRequest,
    UnavailableBriefSection,
    generate_daily_brief_detail_from_metric_snapshot,
)
from app.metrics.briefs import DailyBriefSectionKind
from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
)
from app.metrics.models import DailyBriefRecord
from app.metrics.snapshots import (
    ContributionComponentSource,
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
    persist_metric_snapshot,
)
from app.models.brand import Brand


class _GenerationMetricSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=30_000, currency=request.currency),
                source_ref="shopify_orders",
                source_timestamp=datetime(2026, 6, 17, 13, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 13, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["order:3001"],
            ),
            MetricComponentInput(
                kind=ComponentKind.ATTRIBUTED_AD_SPEND,
                amount=Money(minor=4_500, currency=request.currency),
                source_ref="ads",
                source_timestamp=datetime(2026, 6, 17, 13, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 13, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.STALE,
                evidence_refs=["ad_report:campaign_1"],
            ),
        ]


@pytest.mark.asyncio
async def test_generate_daily_brief_from_metric_snapshot_is_idempotent_and_evidenced() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Generation Brand")
        session.add(brand)
        await session.flush()
        metric_record = await _persist_metric(session, brand)
        request = DailyBriefFromMetricRequest(
            brand_id=brand.id,
            store_id="store_generation",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
            metric_snapshot_id=str(metric_record.id),
            unavailable_sections=(
                UnavailableBriefSection(
                    kind=DailyBriefSectionKind.ACTIONS,
                    reason="A02 action summary input is unavailable.",
                    evidence_refs=("interface:A02",),
                ),
            ),
            generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
            trace_id="trace_brief_generation",
        )

        first = await generate_daily_brief_detail_from_metric_snapshot(session, request)
        second = await generate_daily_brief_detail_from_metric_snapshot(session, request)
        brief_count = (await session.exec(select(func.count()).select_from(DailyBriefRecord))).one()

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert brief_count == 1
    assert first.trace_id == "trace_brief_generation"
    assert first.metric_snapshot_ids == [str(metric_record.id)]
    assert first.coverage.status == SourceCoverage.PARTIAL.value
    assert "Estimated contribution margin: USD 255.00" in first.deterministic_fallback_text
    economics = first.sections[0]
    assert economics.kind == DailyBriefSectionKind.ECONOMICS.value
    assert f"metric_snapshot:{metric_record.id}" in economics.evidence_refs
    assert "order:3001" in economics.evidence_refs
    assert "ad_report:campaign_1" in economics.evidence_refs
    actions = next(section for section in first.sections if section.kind == "actions")
    assert actions.coverage == SourceCoverage.MISSING.value
    assert actions.freshness == FreshnessStatus.UNAVAILABLE.value
    assert actions.evidence_refs == ["interface:A02"]
    assert "audited profit" not in first.deterministic_fallback_text.lower()
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_daily_brief_from_metric_snapshot_rejects_mismatched_scope() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Generation Mismatch Brand")
        session.add(brand)
        await session.flush()
        metric_record = await _persist_metric(session, brand)
        result = await generate_daily_brief_detail_from_metric_snapshot(
            session,
            DailyBriefFromMetricRequest(
                brand_id=brand.id,
                store_id="another_store",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
                metric_snapshot_id=str(metric_record.id),
            ),
        )
        brief_count = (await session.exec(select(func.count()).select_from(DailyBriefRecord))).one()

    assert result is None
    assert brief_count == 0
    await engine.dispose()


async def _persist_metric(session: AsyncSession, brand: Brand):
    metric = await generate_estimated_contribution_margin_snapshot(
        MetricSnapshotRequest(
            brand_id=str(brand.id),
            store_id="store_generation",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
            currency="USD",
            attribution_window_days=7,
            fx_basis="provider_daily_close",
        ),
        source=_GenerationMetricSource(),
    )
    return await persist_metric_snapshot(
        session,
        brand_id=brand.id,
        snapshot=metric,
        trace_id="trace_metric_generation",
    )
