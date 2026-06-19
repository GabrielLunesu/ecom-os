from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

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
from app.metrics.read_models import get_daily_brief_delivery_packet
from app.models.brand import Brand


@pytest.mark.asyncio
async def test_delivery_packet_allows_pending_and_failed_dispatch_only() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Delivery Packet Brand")
        session.add(brand)
        await session.flush()
        brief = await _persist_brief(session, brand)
        intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=brief.id,
            target_platform="hermes_native",
            target_channel_ref="ops",
            body_text=brief.deterministic_fallback_text,
            trace_id="trace_delivery_packet",
        )

        ready = await get_daily_brief_delivery_packet(session, intent_id=str(intent.id))
        assert ready is not None
        assert ready.dispatch_allowed is True
        assert ready.dispatch_status == "ready"
        assert ready.body_hash_matches_intent is True
        assert ready.idempotency_key == intent.idempotency_key
        assert ready.body_text == brief.deterministic_fallback_text
        assert {"type": "daily_brief", "id": str(brief.id)} in ready.evidence
        assert "Use Hermes-native channel delivery only." in ready.guardrails

        delivered_intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=brief.id,
            target_platform="hermes_native",
            target_channel_ref="ops-delivered",
            body_text=brief.deterministic_fallback_text,
            trace_id="trace_delivery_packet_delivered",
        )
        delivered_intent = await record_daily_brief_delivery_result(
            session,
            intent_id=delivered_intent.id,
            status="delivered",
            delivery_evidence={"provider": "hermes", "message_id": "msg_123"},
            trace_id="trace_delivery_delivered",
            delivered_at=datetime(2026, 6, 18, 8, 5, tzinfo=timezone.utc),
        )
        assert delivered_intent is not None
        delivered_packet = await get_daily_brief_delivery_packet(
            session,
            intent_id=str(delivered_intent.id),
        )
        assert delivered_packet is not None
        assert delivered_packet.dispatch_allowed is False
        assert delivered_packet.dispatch_status == "already_delivered"
        assert any("already delivered" in warning for warning in delivered_packet.warnings)

        failed_intent = await record_daily_brief_delivery_result(
            session,
            intent_id=intent.id,
            status="failed",
            delivery_evidence={"provider": "hermes", "attempt": "first"},
            trace_id="trace_delivery_failed",
            error="channel unavailable",
        )
        assert failed_intent is not None
        retryable = await get_daily_brief_delivery_packet(
            session,
            intent_id=str(failed_intent.id),
        )
        assert retryable is not None
        assert retryable.dispatch_allowed is True
        assert retryable.dispatch_status == "retryable"
        assert any("Previous delivery attempt failed" in warning for warning in retryable.warnings)

        unknown_intent = await record_daily_brief_delivery_result(
            session,
            intent_id=intent.id,
            status="outcome_unknown",
            delivery_evidence={"provider": "hermes", "attempt": "second"},
            trace_id="trace_delivery_unknown",
            error="timeout after dispatch",
        )
        assert unknown_intent is not None
        blocked = await get_daily_brief_delivery_packet(
            session,
            intent_id=str(unknown_intent.id),
        )

    assert blocked is not None
    assert blocked.dispatch_allowed is False
    assert blocked.dispatch_status == "reconcile_before_retry"
    assert any("outcome is unknown" in warning for warning in blocked.warnings)
    await engine.dispose()


@pytest.mark.asyncio
async def test_delivery_packet_blocks_body_hash_mismatch_after_narration_edit() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Delivery Packet Body Hash Brand")
        session.add(brand)
        await session.flush()
        brief = await _persist_brief(session, brand)
        intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=brief.id,
            target_platform="hermes_native",
            target_channel_ref="ops",
            body_text=brief.deterministic_fallback_text,
            trace_id="trace_delivery_packet",
        )
        narrated = await record_daily_brief_narration_result(
            session,
            brief_id=brief.id,
            narration_status="completed",
            narrated_text="Narrated brief body with unchanged numbers.",
            trace_id="trace_narration_completed",
        )
        assert narrated is not None
        packet = await get_daily_brief_delivery_packet(session, intent_id=str(intent.id))

    assert packet is not None
    assert packet.body_text == "Narrated brief body with unchanged numbers."
    assert packet.body_hash_matches_intent is False
    assert packet.dispatch_allowed is False
    assert packet.dispatch_status == "body_hash_mismatch"
    assert any("body hash differs" in warning for warning in packet.warnings)
    await engine.dispose()


async def _persist_brief(session: AsyncSession, brand: Brand):
    snapshot = generate_daily_brief_snapshot(
        DailyBriefRequest(
            brand_id=str(brand.id),
            store_id="store_delivery_packet",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
        ),
        sections=[
            DailyBriefSection(
                kind=DailyBriefSectionKind.ECONOMICS,
                title="Economics",
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.CURRENT,
                items=(
                    DailyBriefItem(
                        label="Estimated contribution margin",
                        value="USD 20.00",
                        detail="Costs are partial.",
                        evidence_refs=("metric_snapshot:snap_123",),
                    ),
                ),
                evidence_refs=("metric_snapshot:snap_123",),
            )
        ],
        metric_snapshot_ids=["snap_123"],
        generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
        trace_id="trace_brief_packet",
    )
    return await persist_daily_brief_snapshot(session, brand_id=brand.id, snapshot=snapshot)
