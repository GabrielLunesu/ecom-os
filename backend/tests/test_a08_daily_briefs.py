from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.briefs import (
    DailyBriefItem,
    DailyBriefRequest,
    DailyBriefSection,
    DailyBriefSectionKind,
    body_hash,
    ensure_daily_brief_delivery_intent,
    generate_daily_brief_snapshot,
    persist_daily_brief_snapshot,
    record_daily_brief_delivery_result,
    record_daily_brief_narration_result,
)
from app.metrics.formulas import FreshnessStatus, SourceCoverage
from app.metrics.models import DailyBriefDeliveryIntentRecord, DailyBriefRecord
from app.models.brand import Brand


def _economics_section() -> DailyBriefSection:
    return DailyBriefSection(
        kind=DailyBriefSectionKind.ECONOMICS,
        title="Economics",
        coverage=SourceCoverage.PARTIAL,
        freshness=FreshnessStatus.CURRENT,
        items=(
            DailyBriefItem(
                label="Estimated contribution margin",
                value="USD 20.00",
                detail="COGS, fees, ad spend, and FX are missing.",
                evidence_refs=("metric_snapshot:snap_123",),
            ),
        ),
        warnings=("Missing contribution components reduce coverage.",),
        evidence_refs=("metric_snapshot:snap_123",),
    )


def test_daily_brief_snapshot_is_deterministic_and_marks_missing_sections() -> None:
    request = DailyBriefRequest(
        brand_id="brand_1",
        store_id="store_1",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
    )

    snapshot = generate_daily_brief_snapshot(
        request,
        sections=[_economics_section()],
        metric_snapshot_ids=["snap_123"],
        generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
        trace_id="trace_brief_1",
    )

    assert snapshot.coverage == SourceCoverage.PARTIAL
    assert snapshot.coverage_percent < 100
    assert len(snapshot.sections) == 7
    assert snapshot.sections[0].kind == DailyBriefSectionKind.ECONOMICS
    assert snapshot.sections[1].coverage == SourceCoverage.MISSING
    assert "Estimated contribution margin: USD 20.00" in snapshot.deterministic_fallback_text
    assert "Customer support: missing, unavailable" in snapshot.deterministic_fallback_text
    assert "audited profit" not in snapshot.deterministic_fallback_text.lower()
    assert snapshot.fallback_body_hash == body_hash(snapshot.deterministic_fallback_text)
    assert any("Missing daily brief section" in warning for warning in snapshot.warnings)


@pytest.mark.asyncio
async def test_daily_brief_snapshot_and_delivery_intent_are_idempotent() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Brand")
        session.add(brand)
        await session.flush()
        snapshot = generate_daily_brief_snapshot(
            DailyBriefRequest(
                brand_id=str(brand.id),
                store_id="store_1",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
            ),
            sections=[_economics_section()],
            metric_snapshot_ids=["snap_123"],
            generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
            trace_id="trace_brief_1",
        )

        first = await persist_daily_brief_snapshot(
            session,
            brand_id=brand.id,
            snapshot=snapshot,
        )
        second = await persist_daily_brief_snapshot(
            session,
            brand_id=brand.id,
            snapshot=snapshot,
        )
        first_intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=first.id,
            target_platform="hermes_native",
            target_channel_ref="home",
            body_text=snapshot.deterministic_fallback_text,
            trace_id="trace_delivery_1",
        )
        second_intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=first.id,
            target_platform="hermes_native",
            target_channel_ref="home",
            body_text=snapshot.deterministic_fallback_text,
            trace_id="trace_delivery_2",
        )

        brief_count = (await session.exec(select(func.count()).select_from(DailyBriefRecord))).one()
        intent_count = (
            await session.exec(select(func.count()).select_from(DailyBriefDeliveryIntentRecord))
        ).one()

    assert first.id == second.id
    assert first.trace_id == "trace_brief_1"
    assert first.final_body_hash == snapshot.fallback_body_hash
    assert first_intent.id == second_intent.id
    assert first_intent.trace_id == "trace_delivery_1"
    assert first_intent.status == "pending"
    assert brief_count == 1
    assert intent_count == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_narration_failure_keeps_deterministic_fallback_as_final_text() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Narration Brand")
        session.add(brand)
        await session.flush()
        snapshot = generate_daily_brief_snapshot(
            DailyBriefRequest(
                brand_id=str(brand.id),
                store_id="store_1",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
            ),
            sections=[_economics_section()],
            metric_snapshot_ids=["snap_123"],
            generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
            trace_id="trace_brief_1",
        )
        brief = await persist_daily_brief_snapshot(session, brand_id=brand.id, snapshot=snapshot)

        updated = await record_daily_brief_narration_result(
            session,
            brief_id=brief.id,
            narration_status="failed",
            hermes_session_id="hermes_session_1",
            hermes_run_id="hermes_run_1",
            hermes_cron_ref="cron_daily",
            trace_id="trace_narration_failed",
            error="model unavailable",
        )

    assert updated is not None
    assert updated.narration_status == "failed"
    assert updated.narration_error == "model unavailable"
    assert updated.final_text == snapshot.deterministic_fallback_text
    assert updated.final_body_hash == snapshot.fallback_body_hash
    assert updated.hermes_run_id == "hermes_run_1"
    assert updated.trace_id == "trace_narration_failed"
    await engine.dispose()


@pytest.mark.asyncio
async def test_delivery_result_records_attempts_evidence_and_status() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        brand = Brand(name="A08 Brief Delivery Brand")
        session.add(brand)
        await session.flush()
        snapshot = generate_daily_brief_snapshot(
            DailyBriefRequest(
                brand_id=str(brand.id),
                store_id="store_1",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
            ),
            sections=[_economics_section()],
            metric_snapshot_ids=["snap_123"],
            generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
            trace_id="trace_brief_1",
        )
        brief = await persist_daily_brief_snapshot(session, brand_id=brand.id, snapshot=snapshot)
        intent = await ensure_daily_brief_delivery_intent(
            session,
            brief_id=brief.id,
            target_platform="hermes_native",
            target_channel_ref="home",
            body_text=snapshot.deterministic_fallback_text,
            trace_id="trace_delivery_1",
        )

        failed = await record_daily_brief_delivery_result(
            session,
            intent_id=intent.id,
            status="failed",
            delivery_evidence={"provider": "hermes", "attempt": "first"},
            trace_id="trace_delivery_failed",
            error="channel unavailable",
        )
        assert failed is not None
        assert failed.status == "failed"
        assert failed.attempt_count == 1
        assert failed.delivery_evidence == {"provider": "hermes", "attempt": "first"}
        assert failed.error == "channel unavailable"

        delivered = await record_daily_brief_delivery_result(
            session,
            intent_id=intent.id,
            status="delivered",
            delivery_evidence={"provider": "hermes", "message_id": "msg_123"},
            trace_id="trace_delivery_delivered",
            delivered_at=datetime(2026, 6, 18, 8, 5, tzinfo=timezone.utc),
        )

    assert delivered is not None
    assert delivered.status == "delivered"
    assert delivered.attempt_count == 2
    assert delivered.delivery_evidence == {"provider": "hermes", "message_id": "msg_123"}
    assert delivered.error is None
    assert delivered.delivered_at is not None
    assert delivered.delivered_at.replace(tzinfo=timezone.utc) == datetime(
        2026,
        6,
        18,
        8,
        5,
        tzinfo=timezone.utc,
    )
    await engine.dispose()
