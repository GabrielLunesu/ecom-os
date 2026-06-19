from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.api import (
    DailyBriefDeliveryIntentIn,
    DailyBriefDeliveryResultIn,
    DailyBriefGenerateFromMetricIn,
    DailyBriefGenerateIn,
    DailyBriefItemIn,
    DailyBriefNarrationResultIn,
    DailyBriefSectionIn,
    UnavailableBriefSectionIn,
    daily_brief_card,
    daily_brief_delivery_dispatch_packet,
    daily_brief_delivery_intents,
    daily_brief_detail,
    ensure_daily_brief_delivery_intent_handler,
    generate_daily_brief,
    generate_daily_brief_from_metric,
    latest_daily_brief,
    latest_daily_brief_card,
    latest_metric_card,
    latest_metric_snapshot,
    metric_card,
    metric_snapshot_detail,
    metric_snapshot_explain_context,
    record_daily_brief_delivery_result_handler,
    record_daily_brief_narration_result_handler,
)
from app.metrics.briefs import DailyBriefSectionKind
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
from app.models.brand import Brand


class _ApiSource(ContributionComponentSource):
    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=11_000, currency=request.currency),
                source_ref="orders",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:orders"],
            )
        ]


async def _session_with_snapshot() -> tuple[AsyncSession, str]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="A08 API Brand")
    session.add(brand)
    await session.flush()
    request = MetricSnapshotRequest(
        brand_id=str(brand.id),
        store_id="store_api",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )
    snapshot = await generate_estimated_contribution_margin_snapshot(request, source=_ApiSource())
    record = await persist_metric_snapshot(
        session,
        brand_id=brand.id,
        snapshot=snapshot,
        trace_id="trace_api",
    )
    return session, str(record.id)


@pytest.mark.asyncio
async def test_finance_router_handlers_return_snapshot_and_explain_context() -> None:
    session, snapshot_id = await _session_with_snapshot()
    try:
        latest = await latest_metric_snapshot(
            store_id="store_api",
            metric_name="estimated_contribution_margin",
            currency="USD",
            session=session,
        )
        detail = await metric_snapshot_detail(snapshot_id=snapshot_id, session=session)
        latest_card = await latest_metric_card(
            store_id="store_api",
            metric_name="estimated_contribution_margin",
            currency="USD",
            session=session,
        )
        card = await metric_card(snapshot_id=snapshot_id, session=session)
        explain = await metric_snapshot_explain_context(snapshot_id=snapshot_id, session=session)
    finally:
        await session.close()

    assert latest.id == snapshot_id
    assert detail.id == snapshot_id
    assert latest_card.snapshot_id == snapshot_id
    assert card.snapshot_id == snapshot_id
    assert latest.value == detail.value
    assert latest_card.value == detail.value
    assert card.detail_ref == f"/finance/metric-snapshots/{snapshot_id}"
    assert card.component_count == 1
    assert explain.snapshot.id == snapshot_id
    assert explain.narration_guardrails[0] == "Do not recalculate or alter metric values."


@pytest.mark.asyncio
async def test_finance_router_handlers_return_not_found_for_missing_snapshot() -> None:
    session, _snapshot_id = await _session_with_snapshot()
    try:
        with pytest.raises(HTTPException) as exc_info:
            await latest_metric_snapshot(
                store_id="missing_store",
                metric_name="estimated_contribution_margin",
                currency="USD",
                session=session,
            )
    finally:
        await session.close()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "metric snapshot not found"


async def _session_with_brand() -> tuple[AsyncSession, Brand]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="A08 Brief API Brand")
    session.add(brand)
    await session.flush()
    return session, brand


def _brief_payload(brand: Brand) -> DailyBriefGenerateIn:
    return DailyBriefGenerateIn(
        brand_id=brand.id,
        store_id="store_brief_api",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        sections=[
            DailyBriefSectionIn(
                kind="economics",
                title="Economics",
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.CURRENT,
                items=[
                    DailyBriefItemIn(
                        label="Estimated contribution margin",
                        value="USD 20.00",
                        detail="COGS and ad spend are missing.",
                        evidence_refs=["metric_snapshot:snap_123"],
                    )
                ],
                warnings=["Missing contribution components reduce coverage."],
                evidence_refs=["metric_snapshot:snap_123"],
            )
        ],
        metric_snapshot_ids=["snap_123"],
        generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
        trace_id="trace_brief_api",
    )


@pytest.mark.asyncio
async def test_finance_router_handlers_generate_read_and_prepare_daily_brief_delivery() -> None:
    session, brand = await _session_with_brand()
    try:
        generated = await generate_daily_brief(payload=_brief_payload(brand), session=session)
        latest = await latest_daily_brief(
            store_id="store_brief_api",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
            session=session,
        )
        detail = await daily_brief_detail(brief_id=generated.id, session=session)
        card_before_delivery = await daily_brief_card(brief_id=generated.id, session=session)
        narrated = await record_daily_brief_narration_result_handler(
            brief_id=generated.id,
            payload=DailyBriefNarrationResultIn(
                narration_status="failed",
                hermes_session_id="hermes_session_api",
                hermes_run_id="hermes_run_api",
                hermes_cron_ref="cron_daily",
                trace_id="trace_narration_api",
                error="model unavailable",
            ),
            session=session,
        )
        first_intent = await ensure_daily_brief_delivery_intent_handler(
            brief_id=generated.id,
            payload=DailyBriefDeliveryIntentIn(
                target_platform="hermes_native",
                target_channel_ref="home",
                trace_id="trace_delivery_api",
            ),
            session=session,
        )
        second_intent = await ensure_daily_brief_delivery_intent_handler(
            brief_id=generated.id,
            payload=DailyBriefDeliveryIntentIn(
                target_platform="hermes_native",
                target_channel_ref="home",
                trace_id="trace_delivery_api_2",
            ),
            session=session,
        )
        failed_intent = await record_daily_brief_delivery_result_handler(
            intent_id=first_intent.id,
            payload=DailyBriefDeliveryResultIn(
                status="failed",
                delivery_evidence={"provider": "hermes", "attempt": "first"},
                trace_id="trace_delivery_failed_api",
                error="channel unavailable",
            ),
            session=session,
        )
        latest_card = await latest_daily_brief_card(
            store_id="store_brief_api",
            reporting_date=date(2026, 6, 17),
            reporting_timezone="UTC",
            session=session,
        )
        intents = await daily_brief_delivery_intents(brief_id=generated.id, session=session)
        packet = await daily_brief_delivery_dispatch_packet(
            intent_id=first_intent.id,
            session=session,
        )
    finally:
        await session.close()

    assert latest.id == generated.id
    assert detail.id == generated.id
    assert detail.coverage.status == SourceCoverage.PARTIAL.value
    assert "Estimated contribution margin: USD 20.00" in detail.deterministic_fallback_text
    assert narrated.narration_status == "failed"
    assert narrated.narration_error == "model unavailable"
    assert narrated.final_text == generated.deterministic_fallback_text
    assert narrated.final_body_hash == generated.final_body_hash
    assert card_before_delivery.brief_id == generated.id
    assert card_before_delivery.delivery_status == "not_requested"
    assert latest_card.brief_id == generated.id
    assert latest_card.coverage_status == SourceCoverage.PARTIAL.value
    assert latest_card.delivery_status == "failed"
    assert latest_card.pending_delivery_count == 0
    assert latest_card.failed_delivery_count == 1
    assert latest_card.trace_id == "trace_narration_api"
    assert latest_card.detail_ref == f"/finance/daily-briefs/{generated.id}"
    assert any("Missing daily brief section" in warning for warning in latest_card.warnings)
    assert first_intent.id == second_intent.id
    assert failed_intent.id == first_intent.id
    assert failed_intent.status == "failed"
    assert failed_intent.attempt_count == 1
    assert failed_intent.delivery_evidence == {"provider": "hermes", "attempt": "first"}
    assert first_intent.status == "pending"
    assert first_intent.trace_id == "trace_delivery_api"
    assert first_intent.delivered_at is None
    assert [intent.id for intent in intents] == [first_intent.id]
    assert packet.intent.id == first_intent.id
    assert packet.dispatch_allowed is True
    assert packet.dispatch_status == "retryable"
    assert packet.target_platform == "hermes_native"


@pytest.mark.asyncio
async def test_finance_router_generates_daily_brief_from_metric_snapshot() -> None:
    session, snapshot_id = await _session_with_snapshot()
    try:
        brand = Brand(name="A08 API Metric Brief Brand")
        session.add(brand)
        await session.flush()
        generated = await generate_daily_brief_from_metric(
            payload=DailyBriefGenerateFromMetricIn(
                brand_id=brand.id,
                store_id="store_api",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
                metric_snapshot_id=snapshot_id,
                unavailable_sections=[
                    UnavailableBriefSectionIn(
                        kind=DailyBriefSectionKind.INCIDENTS,
                        reason="A02 incident summary is unavailable.",
                        evidence_refs=["interface:A02"],
                    )
                ],
                generated_at=datetime(2026, 6, 18, 8, tzinfo=timezone.utc),
                trace_id="trace_metric_brief_api",
            ),
            session=session,
        )
        generated_again = await generate_daily_brief_from_metric(
            payload=DailyBriefGenerateFromMetricIn(
                brand_id=brand.id,
                store_id="store_api",
                reporting_date=date(2026, 6, 17),
                reporting_timezone="UTC",
                metric_snapshot_id=snapshot_id,
            ),
            session=session,
        )
    finally:
        await session.close()

    assert generated.id == generated_again.id
    assert generated.metric_snapshot_ids == [snapshot_id]
    assert generated.trace_id == "trace_metric_brief_api"
    assert "Estimated contribution margin" in generated.deterministic_fallback_text
    economics = generated.sections[0]
    assert economics.kind == DailyBriefSectionKind.ECONOMICS.value
    assert f"metric_snapshot:{snapshot_id}" in economics.evidence_refs
    assert "evidence:orders" in economics.evidence_refs
    incidents = next(section for section in generated.sections if section.kind == "incidents")
    assert incidents.coverage == SourceCoverage.MISSING.value
    assert incidents.evidence_refs == ["interface:A02"]


@pytest.mark.asyncio
async def test_finance_router_rejects_metric_brief_generation_for_mismatched_scope() -> None:
    session, snapshot_id = await _session_with_snapshot()
    try:
        brand = Brand(name="A08 API Metric Brief Mismatch Brand")
        session.add(brand)
        await session.flush()
        with pytest.raises(HTTPException) as exc_info:
            await generate_daily_brief_from_metric(
                payload=DailyBriefGenerateFromMetricIn(
                    brand_id=brand.id,
                    store_id="wrong_store",
                    reporting_date=date(2026, 6, 17),
                    reporting_timezone="UTC",
                    metric_snapshot_id=snapshot_id,
                ),
                session=session,
            )
    finally:
        await session.close()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "metric snapshot not found for daily brief scope"


@pytest.mark.asyncio
async def test_daily_brief_handlers_return_not_found_for_missing_brief() -> None:
    session, _brand = await _session_with_brand()
    try:
        with pytest.raises(HTTPException) as exc_info:
            await daily_brief_detail(
                brief_id="00000000-0000-0000-0000-000000000000",
                session=session,
            )
    finally:
        await session.close()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "daily brief not found"
