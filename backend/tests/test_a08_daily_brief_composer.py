from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.brief_composer import (
    compose_daily_brief_snapshot,
    economics_section_from_metric_snapshot,
    unavailable_operational_section,
)
from app.metrics.briefs import DailyBriefRequest, DailyBriefSectionKind
from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
)
from app.metrics.read_models import get_metric_snapshot_detail_by_id
from app.metrics.snapshots import (
    ContributionComponentSource,
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
    persist_metric_snapshot,
)
from app.models.brand import Brand


class _BriefMetricSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        collected_at = datetime(2026, 6, 18, 8, 5, tzinfo=timezone.utc)
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=20_000, currency=request.currency),
                source_ref="shopify_orders",
                source_timestamp=datetime(2026, 6, 17, 20, tzinfo=timezone.utc),
                collected_at=collected_at,
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["order:1001"],
            ),
            MetricComponentInput(
                kind=ComponentKind.COGS,
                amount=Money(minor=7_500, currency=request.currency),
                source_ref="cost_catalog",
                source_timestamp=datetime(2026, 6, 17, 18, tzinfo=timezone.utc),
                collected_at=collected_at,
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.STALE,
                evidence_refs=["cost_sku:sku_1"],
            ),
        ]


@pytest.mark.asyncio
async def test_compose_daily_brief_snapshot_uses_metric_snapshot_evidence() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Composer Brand")
        session.add(brand)
        await session.flush()
        metric = await generate_estimated_contribution_margin_snapshot(
            MetricSnapshotRequest(
                brand_id=str(brand.id),
                store_id="store_1",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
                currency="USD",
                attribution_window_days=7,
                fx_basis="provider_daily_close",
            ),
            source=_BriefMetricSource(),
        )
        record = await persist_metric_snapshot(
            session,
            brand_id=brand.id,
            snapshot=metric,
            trace_id="trace_metric_1",
        )
        detail = await get_metric_snapshot_detail_by_id(session, snapshot_id=str(record.id))

    assert detail is not None
    section = economics_section_from_metric_snapshot(detail)
    snapshot = compose_daily_brief_snapshot(
        DailyBriefRequest(
            brand_id=str(brand.id),
            store_id="store_1",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
        ),
        metric_snapshot=detail,
        sections=[
            unavailable_operational_section(
                DailyBriefSectionKind.CUSTOMER_SUPPORT,
                reason="A05 support backlog input is unavailable.",
                evidence_refs=("interface:A05",),
            ),
        ],
        generated_at=datetime(2026, 6, 18, 8, 30, tzinfo=timezone.utc),
    )

    economics = snapshot.sections[0]
    assert section.kind == DailyBriefSectionKind.ECONOMICS
    assert economics.kind == DailyBriefSectionKind.ECONOMICS
    assert snapshot.metric_snapshot_ids == (str(record.id),)
    assert snapshot.trace_id == "trace_metric_1"
    assert len(snapshot.sections) == 7
    assert economics.coverage == SourceCoverage.PARTIAL
    assert economics.freshness == FreshnessStatus.STALE
    assert "USD 125.00 (12500 minor units)" in snapshot.deterministic_fallback_text
    assert "metric_snapshot:" in " ".join(economics.evidence_refs)
    assert "trace:trace_metric_1" in economics.evidence_refs
    assert "order:1001" in economics.evidence_refs
    assert "cost_sku:sku_1" in economics.evidence_refs
    assert any("Missing economics inputs" in warning for warning in economics.warnings)
    assert any(
        section.kind == DailyBriefSectionKind.CUSTOMER_SUPPORT
        and section.coverage == SourceCoverage.MISSING
        and section.freshness == FreshnessStatus.UNAVAILABLE
        for section in snapshot.sections
    )
    assert "audited profit" not in snapshot.deterministic_fallback_text.lower()
    await engine.dispose()


def test_unavailable_operational_section_rejects_economics_override() -> None:
    with pytest.raises(ValueError, match="economics section"):
        unavailable_operational_section(
            DailyBriefSectionKind.ECONOMICS,
            reason="must come from metrics",
        )
