"""Deterministic finance metric formulas for A08.

The metric layer uses integer minor units and explicit source coverage. Connector
payload normalization happens before these formulas; mixed-currency raw inputs must be
converted or represented through an FX component before calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import StrEnum
from zoneinfo import ZoneInfo

ESTIMATED_CONTRIBUTION_MARGIN_VERSION = "estimated_contribution_margin.v1"


class SourceCoverage(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


class FreshnessStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class ComponentKind(StrEnum):
    NET_SALES = "net_sales"
    SHIPPING_REVENUE = "shipping_revenue"
    DISCOUNTS = "discounts"
    REFUNDS_CHARGEBACKS = "refunds_chargebacks"
    COGS = "cogs"
    PAYMENT_MARKETPLACE_FEES = "payment_marketplace_fees"
    SHIPPING_FULFILMENT_COST = "shipping_fulfilment_cost"
    ATTRIBUTED_AD_SPEND = "attributed_ad_spend"
    FX_ADJUSTMENT = "fx_adjustment"


REQUIRED_CONTRIBUTION_COMPONENTS: tuple[ComponentKind, ...] = (
    ComponentKind.NET_SALES,
    ComponentKind.DISCOUNTS,
    ComponentKind.REFUNDS_CHARGEBACKS,
    ComponentKind.COGS,
    ComponentKind.PAYMENT_MARKETPLACE_FEES,
    ComponentKind.SHIPPING_FULFILMENT_COST,
    ComponentKind.ATTRIBUTED_AD_SPEND,
)

_COMPONENT_SIGN: dict[ComponentKind, int] = {
    ComponentKind.NET_SALES: 1,
    ComponentKind.SHIPPING_REVENUE: 1,
    ComponentKind.DISCOUNTS: -1,
    ComponentKind.REFUNDS_CHARGEBACKS: -1,
    ComponentKind.COGS: -1,
    ComponentKind.PAYMENT_MARKETPLACE_FEES: -1,
    ComponentKind.SHIPPING_FULFILMENT_COST: -1,
    ComponentKind.ATTRIBUTED_AD_SPEND: -1,
    ComponentKind.FX_ADJUSTMENT: 1,
}


@dataclass(frozen=True, slots=True)
class Money:
    minor: int
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.minor, int) or isinstance(self.minor, bool):
            raise TypeError("money minor units must be an integer")
        currency = self.currency.upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("money currency must be an ISO 4217 code")
        object.__setattr__(self, "currency", currency)

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(minor=self.minor + other.minor, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(minor=self.minor - other.minor, currency=self.currency)

    def signed(self, sign: int) -> Money:
        return Money(minor=self.minor * sign, currency=self.currency)

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"money currency mismatch: {self.currency} cannot be combined with {other.currency}"
            )


@dataclass(frozen=True, slots=True)
class ReportingWindow:
    local_date: date
    timezone: str
    start_utc: datetime
    end_utc: datetime

    @property
    def duration_hours(self) -> int:
        return int((self.end_utc - self.start_utc).total_seconds() // 3600)


@dataclass(frozen=True, slots=True)
class MetricComponentInput:
    kind: ComponentKind
    amount: Money
    source_ref: str
    source_timestamp: datetime
    collected_at: datetime
    coverage: SourceCoverage
    freshness: FreshnessStatus
    evidence_refs: list[str]


@dataclass(frozen=True, slots=True)
class MetricComponent:
    kind: ComponentKind
    amount: Money
    contribution: Money
    source_ref: str
    source_timestamp: datetime
    collected_at: datetime
    coverage: SourceCoverage
    freshness: FreshnessStatus
    evidence_refs: list[str]


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    metric_name: str
    display_name: str
    formula_version: str
    store_id: str
    window: ReportingWindow
    value: Money
    components: list[MetricComponent]
    currency: str
    attribution_window_days: int
    fx_basis: str
    coverage: SourceCoverage
    coverage_percent: int
    missing_component_kinds: list[ComponentKind]
    warnings: list[str]


def reporting_window_for_local_day(local_day: date, timezone_name: str) -> ReportingWindow:
    tz = ZoneInfo(timezone_name)
    local_start = datetime.combine(local_day, time.min, tzinfo=tz)
    next_day = local_day.toordinal() + 1
    local_end = datetime.combine(date.fromordinal(next_day), time.min, tzinfo=tz)
    return ReportingWindow(
        local_date=local_day,
        timezone=timezone_name,
        start_utc=local_start.astimezone(timezone.utc),
        end_utc=local_end.astimezone(timezone.utc),
    )


def choose_preferred_component(
    candidates: list[MetricComponentInput],
    *,
    source_precedence: list[str],
) -> MetricComponentInput:
    if not candidates:
        raise ValueError("at least one component candidate is required")
    for source_ref in source_precedence:
        for candidate in candidates:
            if candidate.source_ref == source_ref:
                return candidate
    return candidates[0]


def calculate_estimated_contribution_margin(
    *,
    store_id: str,
    window: ReportingWindow,
    currency: str,
    components: list[MetricComponentInput],
    attribution_window_days: int,
    fx_basis: str,
) -> MetricSnapshot:
    target_currency = currency.upper()
    normalized_components = _dedupe_components(components)
    metric_components: list[MetricComponent] = []
    total = Money(minor=0, currency=target_currency)

    for component in normalized_components:
        if component.amount.currency != target_currency:
            raise ValueError(
                "component currency must match snapshot currency; normalize FX before calculation"
            )
        contribution = component.amount.signed(_COMPONENT_SIGN[component.kind])
        metric_components.append(
            MetricComponent(
                kind=component.kind,
                amount=component.amount,
                contribution=contribution,
                source_ref=component.source_ref,
                source_timestamp=component.source_timestamp,
                collected_at=component.collected_at,
                coverage=component.coverage,
                freshness=component.freshness,
                evidence_refs=list(component.evidence_refs),
            )
        )
        total += contribution

    missing = _missing_components(metric_components)
    coverage_percent = _coverage_percent(metric_components, missing)
    warnings = _coverage_warnings(metric_components, missing)
    coverage = _snapshot_coverage(metric_components, missing)

    return MetricSnapshot(
        metric_name="estimated_contribution_margin",
        display_name="Estimated contribution margin",
        formula_version=ESTIMATED_CONTRIBUTION_MARGIN_VERSION,
        store_id=store_id,
        window=window,
        value=total,
        components=metric_components,
        currency=target_currency,
        attribution_window_days=attribution_window_days,
        fx_basis=fx_basis,
        coverage=coverage,
        coverage_percent=coverage_percent,
        missing_component_kinds=missing,
        warnings=warnings,
    )


def _dedupe_components(components: list[MetricComponentInput]) -> list[MetricComponentInput]:
    selected: dict[ComponentKind, MetricComponentInput] = {}
    for component in components:
        selected[component.kind] = component
    return list(selected.values())


def _missing_components(components: list[MetricComponent]) -> list[ComponentKind]:
    present = {component.kind for component in components}
    return [kind for kind in REQUIRED_CONTRIBUTION_COMPONENTS if kind not in present]


def _coverage_percent(components: list[MetricComponent], missing: list[ComponentKind]) -> int:
    component_by_kind = {component.kind: component for component in components}
    score = 0.0
    for kind in REQUIRED_CONTRIBUTION_COMPONENTS:
        component = component_by_kind.get(kind)
        if component is None:
            continue
        if (
            component.coverage == SourceCoverage.COMPLETE
            and component.freshness == FreshnessStatus.CURRENT
        ):
            score += 1.0
        elif component.coverage != SourceCoverage.MISSING:
            score += 0.5
    denominator = len(REQUIRED_CONTRIBUTION_COMPONENTS)
    if denominator == 0:
        return 100
    if len(missing) == denominator:
        return 0
    return int(round((score / denominator) * 100))


def _coverage_warnings(
    components: list[MetricComponent],
    missing: list[ComponentKind],
) -> list[str]:
    warnings: list[str] = []
    if missing:
        missing_names = ", ".join(kind.value for kind in missing)
        warnings.append(f"Missing contribution components reduce coverage: {missing_names}.")
    partial = [
        component.kind.value
        for component in components
        if component.coverage == SourceCoverage.PARTIAL
    ]
    if partial:
        warnings.append(f"Partial source coverage for: {', '.join(partial)}.")
    stale = [
        component.kind.value
        for component in components
        if component.freshness == FreshnessStatus.STALE
    ]
    if stale:
        warnings.append(f"Stale source data for: {', '.join(stale)}.")
    unavailable = [
        component.kind.value
        for component in components
        if component.freshness == FreshnessStatus.UNAVAILABLE
        or component.coverage == SourceCoverage.MISSING
    ]
    if unavailable:
        warnings.append(f"Unavailable source data for: {', '.join(unavailable)}.")
    return warnings


def _snapshot_coverage(
    components: list[MetricComponent],
    missing: list[ComponentKind],
) -> SourceCoverage:
    if len(missing) == len(REQUIRED_CONTRIBUTION_COMPONENTS):
        return SourceCoverage.MISSING
    if missing:
        return SourceCoverage.PARTIAL
    for component in components:
        if component.coverage != SourceCoverage.COMPLETE:
            return SourceCoverage.PARTIAL
        if component.freshness != FreshnessStatus.CURRENT:
            return SourceCoverage.PARTIAL
    return SourceCoverage.COMPLETE
