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
from app.metrics.tools import DAILY_BRIEF_TOOL_DEFINITIONS, daily_brief_tool_handlers
from app.models.brand import Brand


class _ToolMetricSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=16_000, currency=request.currency),
                source_ref="orders",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:orders"],
            )
        ]


async def _session_with_brand() -> tuple[AsyncSession, Brand]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="A08 Brief Tool Brand")
    session.add(brand)
    await session.flush()
    return session, brand


def test_daily_brief_tool_definitions_are_versioned_and_do_not_send_channels() -> None:
    definitions = {definition.name: definition for definition in DAILY_BRIEF_TOOL_DEFINITIONS}

    assert set(definitions) == {
        "ecom.daily_brief.get",
        "ecom.daily_brief.generate",
        "ecom.daily_brief.generate_from_metric",
        "ecom.daily_brief.delivery_intent.ensure",
        "ecom.daily_brief.delivery_intent.dispatch_packet.get",
        "ecom.daily_brief.narration_result.record",
        "ecom.daily_brief.delivery_result.record",
    }
    assert definitions["ecom.daily_brief.get"].read_or_write == "read"
    assert definitions["ecom.daily_brief.generate"].read_or_write == "write"
    assert definitions["ecom.daily_brief.generate_from_metric"].read_or_write == "write"
    assert definitions["ecom.daily_brief.delivery_intent.ensure"].read_or_write == "write"
    assert (
        definitions["ecom.daily_brief.delivery_intent.dispatch_packet.get"].read_or_write == "read"
    )
    assert definitions["ecom.daily_brief.narration_result.record"].read_or_write == "write"
    assert definitions["ecom.daily_brief.delivery_result.record"].read_or_write == "write"
    assert "does not send a channel message" in definitions["ecom.daily_brief.generate"].description
    assert (
        "does not send a channel message"
        in definitions["ecom.daily_brief.generate_from_metric"].description
    )
    assert (
        "does not call Slack" in definitions["ecom.daily_brief.delivery_intent.ensure"].description
    )
    assert (
        "does not send a channel message"
        in definitions["ecom.daily_brief.delivery_result.record"].description
    )
    for definition in definitions.values():
        assert definition.version == "1.0.0"
        assert definition.required_connection_types == []
    assert definitions["ecom.daily_brief.get"].supports_idempotency is True
    assert definitions["ecom.daily_brief.generate"].supports_idempotency is True
    assert definitions["ecom.daily_brief.generate_from_metric"].supports_idempotency is True
    assert definitions["ecom.daily_brief.delivery_intent.ensure"].supports_idempotency is True
    assert (
        definitions["ecom.daily_brief.delivery_intent.dispatch_packet.get"].supports_idempotency
        is True
    )
    assert definitions["ecom.daily_brief.narration_result.record"].supports_idempotency is True
    assert definitions["ecom.daily_brief.delivery_result.record"].supports_idempotency is False


@pytest.mark.asyncio
async def test_daily_brief_tools_generate_get_and_prepare_pending_delivery_intent() -> None:
    session, brand = await _session_with_brand()
    try:
        handlers = daily_brief_tool_handlers(session)
        generated = await handlers["ecom.daily_brief.generate"](
            {
                "brand_id": str(brand.id),
                "store_id": "store_brief_tool",
                "reporting_date": date(2026, 6, 17).isoformat(),
                "reporting_timezone": "UTC",
                "sections": [
                    {
                        "kind": "economics",
                        "title": "Economics",
                        "coverage": "partial",
                        "freshness": "current",
                        "items": [
                            {
                                "label": "Estimated contribution margin",
                                "value": "USD 20.00",
                                "detail": "COGS and ad spend are missing.",
                                "evidence_refs": ["metric_snapshot:snap_123"],
                            }
                        ],
                        "warnings": ["Missing contribution components reduce coverage."],
                        "evidence_refs": ["metric_snapshot:snap_123"],
                    }
                ],
                "metric_snapshot_ids": ["snap_123"],
                "generated_at": "2026-06-18T08:00:00+00:00",
                "trace_id": "trace_brief_tool",
            }
        )
        brief_id = generated.data["id"]
        fetched = await handlers["ecom.daily_brief.get"]({"brief_id": brief_id})
        delivery = await handlers["ecom.daily_brief.delivery_intent.ensure"](
            {
                "brief_id": brief_id,
                "target_platform": "hermes_native",
                "target_channel_ref": "home",
                "trace_id": "trace_delivery_tool",
            }
        )
        packet = await handlers["ecom.daily_brief.delivery_intent.dispatch_packet.get"](
            {"intent_id": delivery.data["delivery_intent"]["id"]}
        )
        narrated = await handlers["ecom.daily_brief.narration_result.record"](
            {
                "brief_id": brief_id,
                "narration_status": "failed",
                "hermes_session_id": "hermes_session_tool",
                "hermes_run_id": "hermes_run_tool",
                "hermes_cron_ref": "cron_daily",
                "trace_id": "trace_narration_tool",
                "error": "model unavailable",
            }
        )
        failed_delivery = await handlers["ecom.daily_brief.delivery_result.record"](
            {
                "intent_id": delivery.data["delivery_intent"]["id"],
                "status": "failed",
                "delivery_evidence": {"provider": "hermes", "attempt": "first"},
                "trace_id": "trace_delivery_failed_tool",
                "error": "channel unavailable",
            }
        )
        delivery_again = await handlers["ecom.daily_brief.delivery_intent.ensure"](
            {
                "brief_id": brief_id,
                "target_platform": "hermes_native",
                "target_channel_ref": "home",
                "trace_id": "trace_delivery_tool_2",
            }
        )
    finally:
        await session.close()

    assert generated.ok is True
    assert generated.trace_id == "trace_brief_tool"
    assert generated.data["coverage"]["status"] == "partial"
    assert (
        "Estimated contribution margin: USD 20.00" in generated.data["deterministic_fallback_text"]
    )
    assert {"type": "metric_snapshot", "id": "snap_123"} in generated.evidence
    assert fetched.ok is True
    assert fetched.data["id"] == brief_id
    assert delivery.ok is True
    assert delivery.data["delivery_intent"]["status"] == "pending"
    assert delivery.data["delivery_intent"]["delivered_at"] is None
    assert packet.ok is True
    assert packet.data["dispatch_allowed"] is True
    assert packet.data["dispatch_status"] == "ready"
    assert packet.data["idempotency_key"] == delivery.data["delivery_intent"]["idempotency_key"]
    assert narrated.ok is True
    assert narrated.data["narration_status"] == "failed"
    assert narrated.data["narration_error"] == "model unavailable"
    assert narrated.data["final_text"] == generated.data["deterministic_fallback_text"]
    assert failed_delivery.ok is True
    assert failed_delivery.data["delivery_intent"]["status"] == "failed"
    assert failed_delivery.data["delivery_intent"]["attempt_count"] == 1
    assert failed_delivery.data["delivery_intent"]["delivery_evidence"] == {
        "provider": "hermes",
        "attempt": "first",
    }
    assert delivery.data["delivery_intent"]["id"] == delivery_again.data["delivery_intent"]["id"]
    assert delivery.data["delivery_intent"]["trace_id"] == "trace_delivery_tool"


@pytest.mark.asyncio
async def test_daily_brief_tool_generates_from_metric_snapshot() -> None:
    session, brand = await _session_with_brand()
    try:
        metric = await generate_estimated_contribution_margin_snapshot(
            MetricSnapshotRequest(
                brand_id=str(brand.id),
                store_id="store_metric_tool",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
                currency="USD",
                attribution_window_days=7,
                fx_basis="provider_daily_close",
            ),
            source=_ToolMetricSource(),
        )
        metric_record = await persist_metric_snapshot(
            session,
            brand_id=brand.id,
            snapshot=metric,
            trace_id="trace_metric_tool",
        )
        handlers = daily_brief_tool_handlers(session)
        generated = await handlers["ecom.daily_brief.generate_from_metric"](
            {
                "brand_id": str(brand.id),
                "store_id": "store_metric_tool",
                "reporting_date": date(2026, 6, 17).isoformat(),
                "reporting_timezone": "UTC",
                "metric_snapshot_id": str(metric_record.id),
                "unavailable_sections": [
                    {
                        "kind": "health",
                        "reason": "A09 health summary unavailable.",
                        "evidence_refs": ["interface:A09"],
                    }
                ],
                "generated_at": "2026-06-18T08:00:00+00:00",
                "trace_id": "trace_brief_from_metric_tool",
            }
        )
        generated_again = await handlers["ecom.daily_brief.generate_from_metric"](
            {
                "brand_id": str(brand.id),
                "store_id": "store_metric_tool",
                "reporting_date": date(2026, 6, 17).isoformat(),
                "reporting_timezone": "UTC",
                "metric_snapshot_id": str(metric_record.id),
            }
        )
    finally:
        await session.close()

    assert generated.ok is True
    assert generated.trace_id == "trace_brief_from_metric_tool"
    assert generated.data["id"] == generated_again.data["id"]
    assert generated.data["metric_snapshot_ids"] == [str(metric_record.id)]
    assert (
        "Estimated contribution margin: USD 160.00" in generated.data["deterministic_fallback_text"]
    )
    assert {"type": "metric_snapshot", "id": str(metric_record.id)} in generated.evidence
    assert {"type": "daily_brief_section", "id": "interface:A09"} in generated.evidence


@pytest.mark.asyncio
async def test_daily_brief_tool_returns_safe_not_found_result() -> None:
    session, _brand = await _session_with_brand()
    try:
        handlers = daily_brief_tool_handlers(session)
        result = await handlers["ecom.daily_brief.get"](
            {"brief_id": "00000000-0000-0000-0000-000000000000"}
        )
    finally:
        await session.close()

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == {
        "code": "daily_brief_not_found",
        "message": "daily brief not found",
    }
