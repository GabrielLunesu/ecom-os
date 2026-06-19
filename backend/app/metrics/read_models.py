"""Read models for Finance metric drilldowns and explain context."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlmodel import SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.briefs import body_hash
from app.metrics.models import (
    DailyBriefDeliveryIntentRecord,
    DailyBriefRecord,
    MetricComponentRecord,
    MetricSnapshotRecord,
)


class MoneyRead(SQLModel):
    minor: int
    currency: str


class ReportingWindowRead(SQLModel):
    reporting_date: date
    timezone: str
    start_utc: datetime
    end_utc: datetime


class CoverageRead(SQLModel):
    status: str
    percent: int
    freshness: str
    missing_component_kinds: list[str]
    warnings: list[str]


class MetricComponentRead(SQLModel):
    id: str
    kind: str
    amount: MoneyRead
    contribution: MoneyRead
    source_ref: str
    source_timestamp: datetime
    collected_at: datetime
    coverage: str
    freshness: str
    evidence_refs: list[str]


class MetricSnapshotDetail(SQLModel):
    id: str
    metric_name: str
    display_name: str
    formula_version: str
    schema_version: int
    store_id: str
    value: MoneyRead
    window: ReportingWindowRead
    coverage: CoverageRead
    attribution_window_days: int
    fx_basis: str
    trace_id: str | None
    calculation_status: str
    created_at: datetime
    finalized_at: datetime
    components: list[MetricComponentRead]


class MetricExplainContext(SQLModel):
    snapshot: MetricSnapshotDetail
    warnings: list[str]
    narration_guardrails: list[str]


class MetricCardSummary(SQLModel):
    snapshot_id: str
    store_id: str
    title: str
    metric_name: str
    value: MoneyRead
    formula_version: str
    reporting_date: date
    reporting_timezone: str
    window_start_utc: datetime
    window_end_utc: datetime
    coverage_status: str
    coverage_percent: int
    freshness: str
    calculation_status: str
    trace_id: str | None
    warnings: list[str]
    missing_component_kinds: list[str]
    component_count: int
    detail_ref: str


class DailyBriefSectionRead(SQLModel):
    kind: str
    title: str
    coverage: str
    freshness: str
    items: list[dict[str, object]]
    warnings: list[str]
    evidence_refs: list[str]


class DailyBriefDeliveryIntentRead(SQLModel):
    id: str
    brief_id: str
    target_platform: str
    target_channel_ref: str
    idempotency_key: str
    status: str
    body_hash: str
    delivery_evidence: dict[str, object]
    attempt_count: int
    trace_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None


class DailyBriefDeliveryPacket(SQLModel):
    intent: DailyBriefDeliveryIntentRead
    brief_id: str
    store_id: str
    reporting_date: date
    reporting_timezone: str
    target_platform: str
    target_channel_ref: str
    idempotency_key: str
    body_text: str
    body_hash: str
    intent_body_hash: str
    body_hash_matches_intent: bool
    dispatch_allowed: bool
    dispatch_status: str
    trace_id: str | None
    evidence: list[dict[str, str]]
    warnings: list[str]
    guardrails: list[str]


class DailyBriefDetail(SQLModel):
    id: str
    store_id: str
    schema_version: int
    revision: int
    status: str
    window: ReportingWindowRead
    coverage: CoverageRead
    metric_snapshot_ids: list[str]
    sections: list[DailyBriefSectionRead]
    deterministic_fallback_text: str
    final_text: str | None
    final_body_hash: str
    narration_status: str
    narration_error: str | None
    hermes_session_id: str | None
    hermes_run_id: str | None
    hermes_cron_ref: str | None
    trace_id: str | None
    created_at: datetime
    finalized_at: datetime
    delivered_at: datetime | None
    delivery_intents: list[DailyBriefDeliveryIntentRead]


class BriefCardSummary(SQLModel):
    brief_id: str
    store_id: str
    title: str
    status: str
    reporting_date: date
    reporting_timezone: str
    window_start_utc: datetime
    window_end_utc: datetime
    coverage_status: str
    coverage_percent: int
    freshness: str
    narration_status: str
    delivery_status: str
    delivery_target_count: int
    pending_delivery_count: int
    failed_delivery_count: int
    outcome_unknown_delivery_count: int
    delivered_at: datetime | None
    trace_id: str | None
    warnings: list[str]
    metric_snapshot_ids: list[str]
    detail_ref: str


async def get_metric_snapshot_detail_by_id(
    session: AsyncSession,
    *,
    snapshot_id: str,
) -> MetricSnapshotDetail | None:
    snapshot = (
        await session.exec(
            select(MetricSnapshotRecord).where(
                col(MetricSnapshotRecord.id) == UUID(snapshot_id),
            )
        )
    ).one_or_none()
    if snapshot is None:
        return None
    return await _detail_for_snapshot(session, snapshot)


async def get_metric_snapshot_detail(
    session: AsyncSession,
    *,
    store_id: str,
    metric_name: str,
    currency: str | None = None,
) -> MetricSnapshotDetail | None:
    statement = (
        select(MetricSnapshotRecord)
        .where(col(MetricSnapshotRecord.store_id) == store_id)
        .where(col(MetricSnapshotRecord.metric_name) == metric_name)
        .order_by(col(MetricSnapshotRecord.window_end_at).desc())
        .limit(1)
    )
    if currency is not None:
        statement = statement.where(col(MetricSnapshotRecord.currency) == currency.upper())
    snapshot = (await session.exec(statement)).one_or_none()
    if snapshot is None:
        return None
    return await _detail_for_snapshot(session, snapshot)


async def build_metric_explain_context(
    session: AsyncSession,
    *,
    snapshot_id: str,
) -> MetricExplainContext | None:
    detail = await get_metric_snapshot_detail_by_id(session, snapshot_id=snapshot_id)
    if detail is None:
        return None
    return MetricExplainContext(
        snapshot=detail,
        warnings=list(detail.coverage.warnings),
        narration_guardrails=[
            "Do not recalculate or alter metric values.",
            "Use component evidence and warnings as the source for explanation.",
            "Call the metric estimated contribution margin, not audited profit.",
        ],
    )


async def get_metric_card_summary_by_id(
    session: AsyncSession,
    *,
    snapshot_id: str,
) -> MetricCardSummary | None:
    detail = await get_metric_snapshot_detail_by_id(session, snapshot_id=snapshot_id)
    if detail is None:
        return None
    return metric_card_summary_from_detail(detail)


async def get_latest_metric_card_summary(
    session: AsyncSession,
    *,
    store_id: str,
    metric_name: str,
    currency: str | None = None,
) -> MetricCardSummary | None:
    detail = await get_metric_snapshot_detail(
        session,
        store_id=store_id,
        metric_name=metric_name,
        currency=currency,
    )
    if detail is None:
        return None
    return metric_card_summary_from_detail(detail)


def metric_card_summary_from_detail(detail: MetricSnapshotDetail) -> MetricCardSummary:
    return MetricCardSummary(
        snapshot_id=detail.id,
        store_id=detail.store_id,
        title=detail.display_name,
        metric_name=detail.metric_name,
        value=detail.value,
        formula_version=detail.formula_version,
        reporting_date=detail.window.reporting_date,
        reporting_timezone=detail.window.timezone,
        window_start_utc=detail.window.start_utc,
        window_end_utc=detail.window.end_utc,
        coverage_status=detail.coverage.status,
        coverage_percent=detail.coverage.percent,
        freshness=detail.coverage.freshness,
        calculation_status=detail.calculation_status,
        trace_id=detail.trace_id,
        warnings=list(detail.coverage.warnings),
        missing_component_kinds=list(detail.coverage.missing_component_kinds),
        component_count=len(detail.components),
        detail_ref=f"/finance/metric-snapshots/{detail.id}",
    )


async def get_daily_brief_detail_by_id(
    session: AsyncSession,
    *,
    brief_id: str,
) -> DailyBriefDetail | None:
    brief = (
        await session.exec(
            select(DailyBriefRecord).where(
                col(DailyBriefRecord.id) == UUID(brief_id),
            )
        )
    ).one_or_none()
    if brief is None:
        return None
    return await _detail_for_brief(session, brief)


async def get_latest_daily_brief_detail(
    session: AsyncSession,
    *,
    store_id: str,
    reporting_date: date | None = None,
    reporting_timezone: str | None = None,
) -> DailyBriefDetail | None:
    statement = (
        select(DailyBriefRecord)
        .where(col(DailyBriefRecord.store_id) == store_id)
        .order_by(
            col(DailyBriefRecord.reporting_date).desc(),
            col(DailyBriefRecord.revision).desc(),
            col(DailyBriefRecord.created_at).desc(),
        )
        .limit(1)
    )
    if reporting_date is not None:
        statement = statement.where(col(DailyBriefRecord.reporting_date) == reporting_date)
    if reporting_timezone is not None:
        statement = statement.where(col(DailyBriefRecord.reporting_timezone) == reporting_timezone)
    brief = (await session.exec(statement)).one_or_none()
    if brief is None:
        return None
    return await _detail_for_brief(session, brief)


async def list_daily_brief_delivery_intents(
    session: AsyncSession,
    *,
    brief_id: str,
) -> list[DailyBriefDeliveryIntentRead]:
    intents = (
        await session.exec(
            select(DailyBriefDeliveryIntentRecord)
            .where(col(DailyBriefDeliveryIntentRecord.brief_id) == UUID(brief_id))
            .order_by(col(DailyBriefDeliveryIntentRecord.created_at).desc()),
        )
    ).all()
    return [_read_delivery_intent(intent) for intent in intents]


async def get_daily_brief_delivery_packet(
    session: AsyncSession,
    *,
    intent_id: str,
) -> DailyBriefDeliveryPacket | None:
    intent = (
        await session.exec(
            select(DailyBriefDeliveryIntentRecord).where(
                col(DailyBriefDeliveryIntentRecord.id) == UUID(intent_id),
            )
        )
    ).one_or_none()
    if intent is None:
        return None
    brief = (
        await session.exec(
            select(DailyBriefRecord).where(
                col(DailyBriefRecord.id) == intent.brief_id,
            )
        )
    ).one_or_none()
    if brief is None:
        return None
    return _delivery_packet_for_intent_and_brief(intent, brief)


async def get_latest_brief_card_summary(
    session: AsyncSession,
    *,
    store_id: str,
    reporting_date: date | None = None,
    reporting_timezone: str | None = None,
) -> BriefCardSummary | None:
    detail = await get_latest_daily_brief_detail(
        session,
        store_id=store_id,
        reporting_date=reporting_date,
        reporting_timezone=reporting_timezone,
    )
    if detail is None:
        return None
    return brief_card_summary_from_detail(detail)


async def get_brief_card_summary_by_id(
    session: AsyncSession,
    *,
    brief_id: str,
) -> BriefCardSummary | None:
    detail = await get_daily_brief_detail_by_id(session, brief_id=brief_id)
    if detail is None:
        return None
    return brief_card_summary_from_detail(detail)


def brief_card_summary_from_detail(detail: DailyBriefDetail) -> BriefCardSummary:
    failed_count = sum(1 for intent in detail.delivery_intents if intent.status == "failed")
    pending_count = sum(1 for intent in detail.delivery_intents if intent.status == "pending")
    delivered_count = sum(1 for intent in detail.delivery_intents if intent.status == "delivered")
    unknown_count = sum(
        1 for intent in detail.delivery_intents if intent.status == "outcome_unknown"
    )
    return BriefCardSummary(
        brief_id=detail.id,
        store_id=detail.store_id,
        title=f"Daily brief - {detail.window.reporting_date.isoformat()}",
        status=detail.status,
        reporting_date=detail.window.reporting_date,
        reporting_timezone=detail.window.timezone,
        window_start_utc=detail.window.start_utc,
        window_end_utc=detail.window.end_utc,
        coverage_status=detail.coverage.status,
        coverage_percent=detail.coverage.percent,
        freshness=detail.coverage.freshness,
        narration_status=detail.narration_status,
        delivery_status=_delivery_status(
            target_count=len(detail.delivery_intents),
            failed_count=failed_count,
            pending_count=pending_count,
            delivered_count=delivered_count,
            unknown_count=unknown_count,
        ),
        delivery_target_count=len(detail.delivery_intents),
        pending_delivery_count=pending_count,
        failed_delivery_count=failed_count,
        outcome_unknown_delivery_count=unknown_count,
        delivered_at=detail.delivered_at,
        trace_id=detail.trace_id,
        warnings=list(detail.coverage.warnings),
        metric_snapshot_ids=list(detail.metric_snapshot_ids),
        detail_ref=f"/finance/daily-briefs/{detail.id}",
    )


async def _detail_for_snapshot(
    session: AsyncSession,
    snapshot: MetricSnapshotRecord,
) -> MetricSnapshotDetail:
    components = (
        await session.exec(
            select(MetricComponentRecord)
            .where(col(MetricComponentRecord.snapshot_id) == snapshot.id)
            .order_by(col(MetricComponentRecord.kind)),
        )
    ).all()
    return MetricSnapshotDetail(
        id=str(snapshot.id),
        metric_name=snapshot.metric_name,
        display_name=snapshot.display_name,
        formula_version=snapshot.formula_version,
        schema_version=snapshot.schema_version,
        store_id=snapshot.store_id,
        value=MoneyRead(minor=snapshot.value_minor, currency=snapshot.currency),
        window=ReportingWindowRead(
            reporting_date=snapshot.reporting_date,
            timezone=snapshot.reporting_timezone,
            start_utc=snapshot.window_start_at,
            end_utc=snapshot.window_end_at,
        ),
        coverage=CoverageRead(
            status=snapshot.coverage,
            percent=snapshot.coverage_percent,
            freshness=snapshot.freshness,
            missing_component_kinds=list(snapshot.missing_component_kinds),
            warnings=list(snapshot.warnings),
        ),
        attribution_window_days=snapshot.attribution_window_days,
        fx_basis=snapshot.fx_basis,
        trace_id=snapshot.trace_id,
        calculation_status=snapshot.calculation_status,
        created_at=snapshot.created_at,
        finalized_at=snapshot.finalized_at,
        components=[
            MetricComponentRead(
                id=str(component.id),
                kind=component.kind,
                amount=MoneyRead(
                    minor=component.amount_minor,
                    currency=component.currency,
                ),
                contribution=MoneyRead(
                    minor=component.contribution_minor,
                    currency=component.currency,
                ),
                source_ref=component.source_ref,
                source_timestamp=component.source_timestamp,
                collected_at=component.collected_at,
                coverage=component.coverage,
                freshness=component.freshness,
                evidence_refs=list(component.evidence_refs),
            )
            for component in components
        ],
    )


async def _detail_for_brief(
    session: AsyncSession,
    brief: DailyBriefRecord,
) -> DailyBriefDetail:
    delivery_intents = await list_daily_brief_delivery_intents(
        session,
        brief_id=str(brief.id),
    )
    return DailyBriefDetail(
        id=str(brief.id),
        store_id=brief.store_id,
        schema_version=brief.schema_version,
        revision=brief.revision,
        status=brief.status,
        window=ReportingWindowRead(
            reporting_date=brief.reporting_date,
            timezone=brief.reporting_timezone,
            start_utc=brief.window_start_at,
            end_utc=brief.window_end_at,
        ),
        coverage=CoverageRead(
            status=brief.coverage,
            percent=brief.coverage_percent,
            freshness=_brief_freshness(brief),
            missing_component_kinds=[],
            warnings=list(brief.warnings),
        ),
        metric_snapshot_ids=list(brief.metric_snapshot_ids),
        sections=[
            DailyBriefSectionRead(
                kind=str(section.get("kind", "")),
                title=str(section.get("title", "")),
                coverage=str(section.get("coverage", "")),
                freshness=str(section.get("freshness", "")),
                items=_list_of_dicts(section.get("items")),
                warnings=_list_of_strings(section.get("warnings")),
                evidence_refs=_list_of_strings(section.get("evidence_refs")),
            )
            for section in brief.sections
        ],
        deterministic_fallback_text=brief.deterministic_fallback_text,
        final_text=brief.final_text,
        final_body_hash=brief.final_body_hash,
        narration_status=brief.narration_status,
        narration_error=brief.narration_error,
        hermes_session_id=brief.hermes_session_id,
        hermes_run_id=brief.hermes_run_id,
        hermes_cron_ref=brief.hermes_cron_ref,
        trace_id=brief.trace_id,
        created_at=brief.created_at,
        finalized_at=brief.finalized_at,
        delivered_at=brief.delivered_at,
        delivery_intents=delivery_intents,
    )


def _read_delivery_intent(
    intent: DailyBriefDeliveryIntentRecord,
) -> DailyBriefDeliveryIntentRead:
    return DailyBriefDeliveryIntentRead(
        id=str(intent.id),
        brief_id=str(intent.brief_id),
        target_platform=intent.target_platform,
        target_channel_ref=intent.target_channel_ref,
        idempotency_key=intent.idempotency_key,
        status=intent.status,
        body_hash=intent.body_hash,
        delivery_evidence=dict(intent.delivery_evidence),
        attempt_count=intent.attempt_count,
        trace_id=intent.trace_id,
        error=intent.error,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
        delivered_at=intent.delivered_at,
    )


def _delivery_packet_for_intent_and_brief(
    intent: DailyBriefDeliveryIntentRecord,
    brief: DailyBriefRecord,
) -> DailyBriefDeliveryPacket:
    text = brief.final_text or brief.deterministic_fallback_text
    current_hash = body_hash(text)
    hash_matches = current_hash == intent.body_hash
    warnings = _delivery_packet_warnings(intent=intent, body_hash_matches=hash_matches)
    return DailyBriefDeliveryPacket(
        intent=_read_delivery_intent(intent),
        brief_id=str(brief.id),
        store_id=brief.store_id,
        reporting_date=brief.reporting_date,
        reporting_timezone=brief.reporting_timezone,
        target_platform=intent.target_platform,
        target_channel_ref=intent.target_channel_ref,
        idempotency_key=intent.idempotency_key,
        body_text=text,
        body_hash=current_hash,
        intent_body_hash=intent.body_hash,
        body_hash_matches_intent=hash_matches,
        dispatch_allowed=_dispatch_allowed(intent=intent, body_hash_matches=hash_matches),
        dispatch_status=_dispatch_status(intent=intent, body_hash_matches=hash_matches),
        trace_id=intent.trace_id or brief.trace_id,
        evidence=_delivery_packet_evidence(intent=intent, brief=brief),
        warnings=warnings,
        guardrails=[
            "A08 does not send native channel messages.",
            "Use Hermes-native channel delivery only.",
            "Use the provided idempotency key for dispatch attempts.",
            "Record delivery result through A08 after the Hermes delivery attempt.",
            "Do not dispatch when dispatch_allowed is false.",
        ],
    )


def _dispatch_allowed(
    *,
    intent: DailyBriefDeliveryIntentRecord,
    body_hash_matches: bool,
) -> bool:
    return body_hash_matches and intent.status in {"pending", "failed"}


def _dispatch_status(
    *,
    intent: DailyBriefDeliveryIntentRecord,
    body_hash_matches: bool,
) -> str:
    if not body_hash_matches:
        return "body_hash_mismatch"
    if intent.status == "outcome_unknown":
        return "reconcile_before_retry"
    if intent.status == "delivered":
        return "already_delivered"
    if intent.status == "pending":
        return "ready"
    if intent.status == "failed":
        return "retryable"
    return intent.status


def _delivery_packet_warnings(
    *,
    intent: DailyBriefDeliveryIntentRecord,
    body_hash_matches: bool,
) -> list[str]:
    warnings: list[str] = []
    if not body_hash_matches:
        warnings.append(
            "Delivery intent body hash differs from the current brief body; create a new "
            "intent before dispatching edited content."
        )
    if intent.status == "outcome_unknown":
        warnings.append(
            "Delivery outcome is unknown; reconcile the provider result before retrying."
        )
    elif intent.status == "delivered":
        warnings.append("Delivery intent is already delivered.")
    elif intent.status == "failed":
        warnings.append("Previous delivery attempt failed; retry is allowed with same intent.")
    return warnings


def _delivery_packet_evidence(
    *,
    intent: DailyBriefDeliveryIntentRecord,
    brief: DailyBriefRecord,
) -> list[dict[str, str]]:
    evidence = [
        {"type": "daily_brief", "id": str(brief.id)},
        {"type": "daily_brief_delivery_intent", "id": str(intent.id)},
        {"type": "idempotency_key", "id": intent.idempotency_key},
    ]
    for metric_snapshot_id in brief.metric_snapshot_ids:
        evidence.append({"type": "metric_snapshot", "id": str(metric_snapshot_id)})
    if brief.trace_id:
        evidence.append({"type": "trace", "id": brief.trace_id})
    if intent.trace_id and intent.trace_id != brief.trace_id:
        evidence.append({"type": "trace", "id": intent.trace_id})
    return evidence


def _brief_freshness(brief: DailyBriefRecord) -> str:
    freshness_values = {
        str(section.get("freshness", "")) for section in brief.sections if isinstance(section, dict)
    }
    if "unavailable" in freshness_values:
        return "unavailable"
    if "stale" in freshness_values:
        return "stale"
    return "current"


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _delivery_status(
    *,
    target_count: int,
    failed_count: int,
    pending_count: int,
    delivered_count: int,
    unknown_count: int,
) -> str:
    if target_count == 0:
        return "not_requested"
    if failed_count > 0:
        return "failed"
    if unknown_count > 0:
        return "outcome_unknown"
    if pending_count > 0:
        return "pending"
    if delivered_count == target_count:
        return "delivered"
    return "partial"
