"""Deterministic daily brief snapshots and fallback rendering for A08."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.metrics.formulas import (
    FreshnessStatus,
    ReportingWindow,
    SourceCoverage,
    reporting_window_for_local_day,
)

if TYPE_CHECKING:
    from app.metrics.models import DailyBriefDeliveryIntentRecord, DailyBriefRecord


DAILY_BRIEF_SCHEMA_VERSION = 1


class DailyBriefSectionKind(StrEnum):
    ECONOMICS = "economics"
    CUSTOMER_SUPPORT = "customer_support"
    ACTIONS = "actions"
    INCIDENTS = "incidents"
    TASKS = "tasks"
    RESEARCH_TODOS = "research_todos"
    HEALTH = "health"


SECTION_TITLES: dict[DailyBriefSectionKind, str] = {
    DailyBriefSectionKind.ECONOMICS: "Economics",
    DailyBriefSectionKind.CUSTOMER_SUPPORT: "Customer support",
    DailyBriefSectionKind.ACTIONS: "External actions",
    DailyBriefSectionKind.INCIDENTS: "Incidents",
    DailyBriefSectionKind.TASKS: "Tasks",
    DailyBriefSectionKind.RESEARCH_TODOS: "Research and todos",
    DailyBriefSectionKind.HEALTH: "Health",
}


SECTION_ORDER: tuple[DailyBriefSectionKind, ...] = (
    DailyBriefSectionKind.ECONOMICS,
    DailyBriefSectionKind.CUSTOMER_SUPPORT,
    DailyBriefSectionKind.ACTIONS,
    DailyBriefSectionKind.INCIDENTS,
    DailyBriefSectionKind.TASKS,
    DailyBriefSectionKind.RESEARCH_TODOS,
    DailyBriefSectionKind.HEALTH,
)


@dataclass(frozen=True, slots=True)
class DailyBriefRequest:
    brand_id: str
    store_id: str
    reporting_date: date
    reporting_timezone: str
    revision: int = 1


@dataclass(frozen=True, slots=True)
class DailyBriefItem:
    label: str
    value: str
    detail: str = ""
    evidence_refs: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "value": self.value,
            "detail": self.detail,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class DailyBriefSection:
    kind: DailyBriefSectionKind
    title: str
    coverage: SourceCoverage
    freshness: FreshnessStatus
    items: tuple[DailyBriefItem, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "title": self.title,
            "coverage": self.coverage.value,
            "freshness": self.freshness.value,
            "items": [item.to_payload() for item in self.items],
            "warnings": list(self.warnings),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class DailyBriefSnapshot:
    brand_id: str
    store_id: str
    revision: int
    schema_version: int
    window: ReportingWindow
    sections: tuple[DailyBriefSection, ...]
    metric_snapshot_ids: tuple[str, ...]
    coverage: SourceCoverage
    coverage_percent: int
    warnings: tuple[str, ...]
    deterministic_fallback_text: str
    fallback_body_hash: str
    generated_at: datetime
    trace_id: str | None = None


def generate_daily_brief_snapshot(
    request: DailyBriefRequest,
    *,
    sections: list[DailyBriefSection],
    metric_snapshot_ids: list[str] | None = None,
    generated_at: datetime | None = None,
    trace_id: str | None = None,
) -> DailyBriefSnapshot:
    ordered_sections = _complete_ordered_sections(sections)
    coverage = _brief_coverage(ordered_sections)
    coverage_percent = _brief_coverage_percent(ordered_sections)
    warnings = _brief_warnings(ordered_sections)
    window = reporting_window_for_local_day(
        request.reporting_date,
        request.reporting_timezone,
    )
    generated = _ensure_aware_utc(generated_at or datetime.now(timezone.utc))
    fallback_text = render_daily_brief_fallback(
        store_id=request.store_id,
        window=window,
        coverage=coverage,
        coverage_percent=coverage_percent,
        sections=ordered_sections,
        warnings=warnings,
    )
    return DailyBriefSnapshot(
        brand_id=request.brand_id,
        store_id=request.store_id,
        revision=request.revision,
        schema_version=DAILY_BRIEF_SCHEMA_VERSION,
        window=window,
        sections=tuple(ordered_sections),
        metric_snapshot_ids=tuple(metric_snapshot_ids or ()),
        coverage=coverage,
        coverage_percent=coverage_percent,
        warnings=tuple(warnings),
        deterministic_fallback_text=fallback_text,
        fallback_body_hash=body_hash(fallback_text),
        generated_at=generated,
        trace_id=trace_id,
    )


def render_daily_brief_fallback(
    *,
    store_id: str,
    window: ReportingWindow,
    coverage: SourceCoverage,
    coverage_percent: int,
    sections: list[DailyBriefSection],
    warnings: list[str],
) -> str:
    lines = [
        f"Daily brief for {store_id} - {window.local_date.isoformat()} ({window.timezone})",
        f"Window: {window.start_utc.isoformat()} to {window.end_utc.isoformat()}",
        f"Coverage: {coverage.value} ({coverage_percent}%)",
    ]
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    for section in sections:
        lines.append("")
        lines.append(f"{section.title}: {section.coverage.value}, {section.freshness.value}")
        if section.items:
            for item in section.items:
                detail = f" - {item.detail}" if item.detail else ""
                lines.append(f"- {item.label}: {item.value}{detail}")
        else:
            lines.append("- No deterministic data available.")
        for warning in section.warnings:
            lines.append(f"- Warning: {warning}")
    return "\n".join(lines)


async def persist_daily_brief_snapshot(
    session: AsyncSession,
    *,
    brand_id: UUID,
    snapshot: DailyBriefSnapshot,
) -> "DailyBriefRecord":
    from app.metrics.models import DailyBriefRecord

    existing = (
        await session.exec(
            select(DailyBriefRecord)
            .where(col(DailyBriefRecord.brand_id) == brand_id)
            .where(col(DailyBriefRecord.store_id) == snapshot.store_id)
            .where(col(DailyBriefRecord.reporting_date) == snapshot.window.local_date)
            .where(col(DailyBriefRecord.reporting_timezone) == snapshot.window.timezone)
            .where(col(DailyBriefRecord.revision) == snapshot.revision),
        )
    ).first()
    if existing is not None:
        return existing

    record = DailyBriefRecord.from_domain(brand_id=brand_id, snapshot=snapshot)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def ensure_daily_brief_delivery_intent(
    session: AsyncSession,
    *,
    brief_id: UUID,
    target_platform: str,
    target_channel_ref: str,
    body_text: str,
    trace_id: str | None = None,
) -> "DailyBriefDeliveryIntentRecord":
    from app.metrics.models import DailyBriefDeliveryIntentRecord

    idempotency_key = daily_brief_delivery_idempotency_key(
        brief_id=brief_id,
        target_platform=target_platform,
        target_channel_ref=target_channel_ref,
    )
    existing = (
        await session.exec(
            select(DailyBriefDeliveryIntentRecord).where(
                col(DailyBriefDeliveryIntentRecord.idempotency_key) == idempotency_key,
            ),
        )
    ).first()
    if existing is not None:
        return existing

    record = DailyBriefDeliveryIntentRecord(
        brief_id=brief_id,
        target_platform=target_platform,
        target_channel_ref=target_channel_ref,
        idempotency_key=idempotency_key,
        body_hash=body_hash(body_text),
        trace_id=trace_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def record_daily_brief_narration_result(
    session: AsyncSession,
    *,
    brief_id: UUID,
    narration_status: str,
    narrated_text: str | None = None,
    hermes_session_id: str | None = None,
    hermes_run_id: str | None = None,
    hermes_cron_ref: str | None = None,
    trace_id: str | None = None,
    error: str | None = None,
) -> "DailyBriefRecord | None":
    from app.metrics.models import DailyBriefRecord

    status = _validated_narration_status(narration_status)
    record = (
        await session.exec(
            select(DailyBriefRecord).where(col(DailyBriefRecord.id) == brief_id),
        )
    ).one_or_none()
    if record is None:
        return None

    record.narration_status = status
    record.hermes_session_id = hermes_session_id
    record.hermes_run_id = hermes_run_id
    record.hermes_cron_ref = hermes_cron_ref
    if trace_id is not None:
        record.trace_id = trace_id
    record.narration_error = error

    if status == "completed":
        final_text = (narrated_text or "").strip()
        if not final_text:
            raise ValueError("completed narration requires final text")
        record.final_text = final_text
        record.final_body_hash = body_hash(final_text)
    else:
        record.final_text = record.deterministic_fallback_text
        record.final_body_hash = body_hash(record.deterministic_fallback_text)

    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def record_daily_brief_delivery_result(
    session: AsyncSession,
    *,
    intent_id: UUID,
    status: str,
    delivery_evidence: dict[str, object] | None = None,
    trace_id: str | None = None,
    error: str | None = None,
    delivered_at: datetime | None = None,
) -> "DailyBriefDeliveryIntentRecord | None":
    from app.metrics.models import DailyBriefDeliveryIntentRecord, DailyBriefRecord

    delivery_status = _validated_delivery_status(status)
    intent = (
        await session.exec(
            select(DailyBriefDeliveryIntentRecord).where(
                col(DailyBriefDeliveryIntentRecord.id) == intent_id,
            ),
        )
    ).one_or_none()
    if intent is None:
        return None

    now = datetime.now(timezone.utc)
    intent.status = delivery_status
    intent.delivery_evidence = dict(delivery_evidence or {})
    intent.attempt_count += 1
    if trace_id is not None:
        intent.trace_id = trace_id
    intent.error = error
    intent.updated_at = now
    if delivery_status == "delivered":
        intent.delivered_at = _ensure_aware_utc(delivered_at or now)
        brief = (
            await session.exec(
                select(DailyBriefRecord).where(col(DailyBriefRecord.id) == intent.brief_id),
            )
        ).one_or_none()
        if brief is not None:
            brief.delivered_at = intent.delivered_at
            session.add(brief)
    elif delivery_status in {"failed", "outcome_unknown"}:
        intent.delivered_at = None

    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    return intent


def daily_brief_delivery_idempotency_key(
    *,
    brief_id: UUID,
    target_platform: str,
    target_channel_ref: str,
) -> str:
    return f"daily_brief:{brief_id}:{target_platform}:{target_channel_ref}"


def body_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _complete_ordered_sections(sections: list[DailyBriefSection]) -> list[DailyBriefSection]:
    by_kind = {section.kind: section for section in sections}
    return [
        by_kind.get(kind)
        or DailyBriefSection(
            kind=kind,
            title=SECTION_TITLES[kind],
            coverage=SourceCoverage.MISSING,
            freshness=FreshnessStatus.UNAVAILABLE,
            warnings=(f"Section unavailable: {SECTION_TITLES[kind]}.",),
        )
        for kind in SECTION_ORDER
    ]


def _brief_coverage(sections: list[DailyBriefSection]) -> SourceCoverage:
    if all(section.coverage == SourceCoverage.MISSING for section in sections):
        return SourceCoverage.MISSING
    if all(
        section.coverage == SourceCoverage.COMPLETE and section.freshness == FreshnessStatus.CURRENT
        for section in sections
    ):
        return SourceCoverage.COMPLETE
    return SourceCoverage.PARTIAL


def _brief_coverage_percent(sections: list[DailyBriefSection]) -> int:
    score = 0.0
    for section in sections:
        if (
            section.coverage == SourceCoverage.COMPLETE
            and section.freshness == FreshnessStatus.CURRENT
        ):
            score += 1.0
        elif section.coverage != SourceCoverage.MISSING:
            score += 0.5
    return int(round((score / len(SECTION_ORDER)) * 100))


def _brief_warnings(sections: list[DailyBriefSection]) -> list[str]:
    warnings: list[str] = []
    for section in sections:
        warnings.extend(section.warnings)
        if section.coverage == SourceCoverage.MISSING:
            warnings.append(f"Missing daily brief section: {section.title}.")
        elif section.coverage == SourceCoverage.PARTIAL:
            warnings.append(f"Partial daily brief section: {section.title}.")
        if section.freshness == FreshnessStatus.STALE:
            warnings.append(f"Stale daily brief section: {section.title}.")
        elif section.freshness == FreshnessStatus.UNAVAILABLE:
            warnings.append(f"Unavailable daily brief section: {section.title}.")
    return _dedupe(warnings)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("daily brief timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _validated_narration_status(value: str) -> str:
    status = value.strip()
    if status not in {"completed", "failed", "unavailable", "not_requested"}:
        raise ValueError("unsupported daily brief narration status")
    return status


def _validated_delivery_status(value: str) -> str:
    status = value.strip()
    if status not in {"pending", "delivered", "failed", "outcome_unknown"}:
        raise ValueError("unsupported daily brief delivery status")
    return status
