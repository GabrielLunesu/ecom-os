"""Deterministic daily brief composition from A08 metric evidence.

This module converts stored metric read models and accepted operational section inputs
into the immutable daily brief snapshot. It does not ask an LLM to summarize or calculate
numbers; narration remains a later A03/Hermes step over the stored snapshot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from app.metrics.briefs import (
    DailyBriefItem,
    DailyBriefRequest,
    DailyBriefSection,
    DailyBriefSectionKind,
    DailyBriefSnapshot,
    generate_daily_brief_snapshot,
)
from app.metrics.formulas import FreshnessStatus, SourceCoverage


class _MoneyForBrief(Protocol):
    minor: int
    currency: str


class _WindowForBrief(Protocol):
    reporting_date: object
    timezone: str
    start_utc: datetime
    end_utc: datetime


class _CoverageForBrief(Protocol):
    status: str
    percent: int
    freshness: str
    missing_component_kinds: list[str]
    warnings: list[str]


class _MetricComponentForBrief(Protocol):
    kind: str
    evidence_refs: list[str]


class MetricSnapshotForBrief(Protocol):
    id: str
    display_name: str
    formula_version: str
    value: _MoneyForBrief
    window: _WindowForBrief
    coverage: _CoverageForBrief
    trace_id: str | None
    components: Sequence[_MetricComponentForBrief]


def compose_daily_brief_snapshot(
    request: DailyBriefRequest,
    *,
    metric_snapshot: MetricSnapshotForBrief | None = None,
    sections: list[DailyBriefSection] | None = None,
    generated_at: datetime | None = None,
    trace_id: str | None = None,
) -> DailyBriefSnapshot:
    """Build a full daily brief snapshot from deterministic section inputs.

    When `metric_snapshot` is supplied it is the economics source of truth and replaces
    any caller-provided economics section. Missing non-economics sections are filled by
    `generate_daily_brief_snapshot` with explicit missing/unavailable coverage.
    """

    provided_sections = list(sections or [])
    if metric_snapshot is not None:
        provided_sections = [
            section
            for section in provided_sections
            if section.kind != DailyBriefSectionKind.ECONOMICS
        ]
        provided_sections.insert(0, economics_section_from_metric_snapshot(metric_snapshot))

    metric_snapshot_ids = [metric_snapshot.id] if metric_snapshot is not None else []
    return generate_daily_brief_snapshot(
        request,
        sections=provided_sections,
        metric_snapshot_ids=metric_snapshot_ids,
        generated_at=generated_at,
        trace_id=trace_id or (metric_snapshot.trace_id if metric_snapshot is not None else None),
    )


def economics_section_from_metric_snapshot(
    snapshot: MetricSnapshotForBrief,
) -> DailyBriefSection:
    evidence_refs = _metric_evidence_refs(snapshot)
    missing = [kind.replace("_", " ") for kind in snapshot.coverage.missing_component_kinds]
    warnings = list(snapshot.coverage.warnings)
    if missing:
        warnings.append(f"Missing economics inputs: {', '.join(missing)}.")

    return DailyBriefSection(
        kind=DailyBriefSectionKind.ECONOMICS,
        title="Economics",
        coverage=SourceCoverage(snapshot.coverage.status),
        freshness=FreshnessStatus(snapshot.coverage.freshness),
        items=(
            DailyBriefItem(
                label=snapshot.display_name,
                value=_format_minor_units(snapshot.value),
                detail=(
                    f"{snapshot.formula_version}; {snapshot.coverage.percent}% coverage; "
                    f"{snapshot.coverage.freshness} freshness."
                ),
                evidence_refs=tuple(evidence_refs),
            ),
            DailyBriefItem(
                label="Reporting window",
                value=(f"{snapshot.window.reporting_date} " f"{snapshot.window.timezone}"),
                detail=(
                    f"{snapshot.window.start_utc.isoformat()} to "
                    f"{snapshot.window.end_utc.isoformat()}"
                ),
                evidence_refs=tuple(evidence_refs),
            ),
            DailyBriefItem(
                label="Formula coverage",
                value=f"{snapshot.coverage.percent}%",
                detail=(
                    f"{snapshot.coverage.status}; "
                    f"missing {', '.join(missing) if missing else 'none'}."
                ),
                evidence_refs=tuple(evidence_refs),
            ),
        ),
        warnings=tuple(_unique(warnings)),
        evidence_refs=tuple(evidence_refs),
    )


def unavailable_operational_section(
    kind: DailyBriefSectionKind,
    *,
    reason: str,
    evidence_refs: tuple[str, ...] = (),
) -> DailyBriefSection:
    """Create an explicit unavailable non-economics section for upstream gaps."""

    if kind == DailyBriefSectionKind.ECONOMICS:
        raise ValueError("economics section must be sourced from metric snapshots")
    return DailyBriefSection(
        kind=kind,
        title=kind.value.replace("_", " ").title(),
        coverage=SourceCoverage.MISSING,
        freshness=FreshnessStatus.UNAVAILABLE,
        warnings=(reason,),
        evidence_refs=evidence_refs,
    )


def _format_minor_units(money: _MoneyForBrief) -> str:
    major = abs(money.minor) // 100
    minor = abs(money.minor) % 100
    sign = "-" if money.minor < 0 else ""
    return f"{money.currency} {sign}{major}.{minor:02d} ({money.minor} minor units)"


def _metric_evidence_refs(snapshot: MetricSnapshotForBrief) -> list[str]:
    refs = [f"metric_snapshot:{snapshot.id}"]
    if snapshot.trace_id:
        refs.append(f"trace:{snapshot.trace_id}")
    for component in snapshot.components:
        refs.append(f"metric_component:{component.kind}")
        refs.extend(component.evidence_refs)
    return _unique(refs)


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
