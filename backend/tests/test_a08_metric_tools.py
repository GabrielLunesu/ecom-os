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
from app.metrics.snapshots import (
    ContributionComponentSource,
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
    persist_metric_snapshot,
)
from app.metrics.tools import METRIC_TOOL_DEFINITIONS, metric_tool_handlers
from app.models.brand import Brand


class _ToolSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=25_000, currency=request.currency),
                source_ref="orders",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:orders"],
            ),
            MetricComponentInput(
                kind=ComponentKind.ATTRIBUTED_AD_SPEND,
                amount=Money(minor=3_000, currency=request.currency),
                source_ref="ads",
                source_timestamp=datetime(2026, 6, 17, 13, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 13, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:ads"],
            ),
        ]


async def _seed(session: AsyncSession) -> str:
    brand = Brand(name="A08 Tool Brand")
    session.add(brand)
    await session.flush()
    request = MetricSnapshotRequest(
        brand_id=str(brand.id),
        store_id="store_tool",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )
    snapshot = await generate_estimated_contribution_margin_snapshot(request, source=_ToolSource())
    record = await persist_metric_snapshot(session, brand_id=brand.id, snapshot=snapshot)
    return str(record.id)


@pytest.mark.asyncio
async def test_metric_tool_definitions_are_read_only_and_versioned() -> None:
    definitions = {definition.name: definition for definition in METRIC_TOOL_DEFINITIONS}

    assert set(definitions) == {"ecom.metric.get", "ecom.metric.explain"}
    for definition in definitions.values():
        assert definition.version == "1.0.0"
        assert definition.read_or_write == "read"
        assert definition.risk_class == "low"
        assert definition.required_connection_types == []
        assert definition.minimum_trace_coverage == "verified"
        assert definition.output_schema["type"] == "object"


@pytest.mark.asyncio
async def test_metric_get_tool_returns_structured_snapshot_with_evidence() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        snapshot_id = await _seed(session)
        handlers = metric_tool_handlers(session)
        result = await handlers["ecom.metric.get"]({"snapshot_id": snapshot_id})

    assert result.ok is True
    assert result.status == "completed"
    assert result.data["id"] == snapshot_id
    assert result.data["value"]["minor"] == 22_000
    assert result.freshness["status"] == "current"
    assert {"type": "metric_component", "id": "evidence:orders"} in result.evidence
    assert any("Missing contribution components" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_metric_explain_tool_returns_guardrails_and_never_profit_label() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        snapshot_id = await _seed(session)
        handlers = metric_tool_handlers(session)
        result = await handlers["ecom.metric.explain"]({"snapshot_id": snapshot_id})

    assert result.ok is True
    assert result.data["snapshot"]["display_name"] == "Estimated contribution margin"
    assert "profit" not in result.data["snapshot"]["display_name"].lower()
    assert result.data["narration_guardrails"][0] == "Do not recalculate or alter metric values."


@pytest.mark.asyncio
async def test_metric_tool_returns_safe_not_found_result() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        handlers = metric_tool_handlers(session)
        result = await handlers["ecom.metric.get"](
            {"snapshot_id": "00000000-0000-0000-0000-000000000000"}
        )

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == {
        "code": "metric_snapshot_not_found",
        "message": "metric snapshot not found",
    }
