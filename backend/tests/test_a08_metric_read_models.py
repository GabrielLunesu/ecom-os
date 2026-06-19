from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
)
from app.metrics.read_models import (
    build_metric_explain_context,
    get_latest_metric_card_summary,
    get_metric_card_summary_by_id,
    get_metric_snapshot_detail,
    get_metric_snapshot_detail_by_id,
)
from app.metrics.snapshots import (
    ContributionComponentSource,
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
    persist_metric_snapshot,
)
from app.models.brand import Brand


class _ReadModelSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=15_000, currency=request.currency),
                source_ref="orders:window:2026-06-17",
                source_timestamp=datetime(2026, 6, 17, 20, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 20, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["order:1001", "order:1002"],
            ),
            MetricComponentInput(
                kind=ComponentKind.PAYMENT_MARKETPLACE_FEES,
                amount=Money(minor=450, currency=request.currency),
                source_ref="fees:stripe",
                source_timestamp=datetime(2026, 6, 17, 21, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 21, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["fee:stripe:batch"],
            ),
        ]


async def _seed_snapshot(session: AsyncSession) -> str:
    brand = Brand(name="A08 Read Brand")
    session.add(brand)
    await session.flush()
    request = MetricSnapshotRequest(
        brand_id=str(brand.id),
        store_id="store_read",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )
    snapshot = await generate_estimated_contribution_margin_snapshot(
        request,
        source=_ReadModelSource(),
    )
    record = await persist_metric_snapshot(
        session,
        brand_id=brand.id,
        snapshot=snapshot,
        trace_id="trace_read",
    )
    return str(record.id)


@pytest.mark.asyncio
async def test_metric_snapshot_detail_exposes_drilldown_evidence_and_coverage() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        snapshot_id = await _seed_snapshot(session)

        detail = await get_metric_snapshot_detail(
            session,
            store_id="store_read",
            metric_name="estimated_contribution_margin",
            currency="USD",
        )

        by_id = await get_metric_snapshot_detail_by_id(session, snapshot_id=snapshot_id)
        latest_card = await get_latest_metric_card_summary(
            session,
            store_id="store_read",
            metric_name="estimated_contribution_margin",
            currency="USD",
        )
        card_by_id = await get_metric_card_summary_by_id(session, snapshot_id=snapshot_id)

    assert detail is not None
    assert by_id is not None
    assert latest_card is not None
    assert card_by_id is not None
    assert detail.id == snapshot_id
    assert by_id.id == snapshot_id
    assert detail.value.minor == 14_550
    assert detail.value.currency == "USD"
    assert detail.window.timezone == "UTC"
    assert detail.coverage.status == SourceCoverage.PARTIAL.value
    assert detail.coverage.percent < 100
    assert detail.trace_id == "trace_read"
    assert {component.kind for component in detail.components} == {
        ComponentKind.NET_SALES.value,
        ComponentKind.PAYMENT_MARKETPLACE_FEES.value,
    }
    assert detail.components[0].evidence_refs == ["order:1001", "order:1002"]
    assert latest_card.snapshot_id == snapshot_id
    assert card_by_id.snapshot_id == snapshot_id
    assert latest_card.value.minor == 14_550
    assert latest_card.coverage_status == SourceCoverage.PARTIAL.value
    assert latest_card.component_count == 2
    assert latest_card.detail_ref == f"/finance/metric-snapshots/{snapshot_id}"
    assert latest_card.missing_component_kinds
    assert any("Missing contribution components" in warning for warning in latest_card.warnings)


@pytest.mark.asyncio
async def test_metric_explain_context_is_structured_and_number_preserving() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        snapshot_id = await _seed_snapshot(session)
        context = await build_metric_explain_context(session, snapshot_id=snapshot_id)

    assert context is not None
    assert context.snapshot.id == snapshot_id
    assert context.snapshot.value.minor == 14_550
    assert context.narration_guardrails == [
        "Do not recalculate or alter metric values.",
        "Use component evidence and warnings as the source for explanation.",
        "Call the metric estimated contribution margin, not audited profit.",
    ]
    assert any("Missing contribution components" in warning for warning in context.warnings)
