from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
    calculate_estimated_contribution_margin,
    choose_preferred_component,
    reporting_window_for_local_day,
)


def _component(
    kind: ComponentKind,
    minor: int,
    *,
    source_ref: str,
    coverage: SourceCoverage = SourceCoverage.COMPLETE,
    freshness: FreshnessStatus = FreshnessStatus.CURRENT,
) -> MetricComponentInput:
    return MetricComponentInput(
        kind=kind,
        amount=Money(minor=minor, currency="USD"),
        source_ref=source_ref,
        source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
        collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
        coverage=coverage,
        freshness=freshness,
        evidence_refs=[f"evidence:{source_ref}"],
    )


def test_estimated_contribution_margin_reconciles_to_components() -> None:
    snapshot = calculate_estimated_contribution_margin(
        store_id="store_1",
        window=reporting_window_for_local_day(date(2026, 6, 17), "America/New_York"),
        currency="USD",
        components=[
            _component(ComponentKind.NET_SALES, 10_000, source_ref="orders"),
            _component(ComponentKind.SHIPPING_REVENUE, 1_000, source_ref="orders"),
            _component(ComponentKind.DISCOUNTS, 500, source_ref="orders"),
            _component(ComponentKind.REFUNDS_CHARGEBACKS, 2_000, source_ref="refunds"),
            _component(ComponentKind.COGS, 4_000, source_ref="costs"),
            _component(ComponentKind.PAYMENT_MARKETPLACE_FEES, 300, source_ref="fees"),
            _component(ComponentKind.SHIPPING_FULFILMENT_COST, 700, source_ref="shipping"),
            _component(ComponentKind.ATTRIBUTED_AD_SPEND, 1_200, source_ref="ads"),
            _component(ComponentKind.FX_ADJUSTMENT, -100, source_ref="fx"),
        ],
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )

    assert snapshot.metric_name == "estimated_contribution_margin"
    assert snapshot.formula_version == "estimated_contribution_margin.v1"
    assert snapshot.value == Money(minor=2_200, currency="USD")
    assert snapshot.coverage == SourceCoverage.COMPLETE
    assert snapshot.coverage_percent == 100
    assert snapshot.missing_component_kinds == []
    assert snapshot.warnings == []
    assert sum(component.contribution.minor for component in snapshot.components) == 2_200
    assert all(isinstance(component.contribution.minor, int) for component in snapshot.components)


def test_missing_or_stale_cost_inputs_reduce_coverage_without_zero_fill_claims() -> None:
    snapshot = calculate_estimated_contribution_margin(
        store_id="store_1",
        window=reporting_window_for_local_day(date(2026, 6, 17), "UTC"),
        currency="USD",
        components=[
            _component(ComponentKind.NET_SALES, 10_000, source_ref="orders"),
            _component(ComponentKind.DISCOUNTS, 500, source_ref="orders"),
            _component(
                ComponentKind.COGS,
                3_800,
                source_ref="manual_cogs",
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.STALE,
            ),
        ],
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )

    assert snapshot.value == Money(minor=5_700, currency="USD")
    assert snapshot.coverage == SourceCoverage.PARTIAL
    assert snapshot.coverage_percent < 100
    assert snapshot.missing_component_kinds == [
        ComponentKind.REFUNDS_CHARGEBACKS,
        ComponentKind.PAYMENT_MARKETPLACE_FEES,
        ComponentKind.SHIPPING_FULFILMENT_COST,
        ComponentKind.ATTRIBUTED_AD_SPEND,
    ]
    assert any("missing" in warning.lower() for warning in snapshot.warnings)
    assert any("stale" in warning.lower() for warning in snapshot.warnings)


def test_mixed_currency_components_require_prior_fx_normalization() -> None:
    with pytest.raises(ValueError, match="currency"):
        calculate_estimated_contribution_margin(
            store_id="store_1",
            window=reporting_window_for_local_day(date(2026, 6, 17), "UTC"),
            currency="USD",
            components=[
                _component(ComponentKind.NET_SALES, 10_000, source_ref="orders"),
                MetricComponentInput(
                    kind=ComponentKind.COGS,
                    amount=Money(minor=4_000, currency="EUR"),
                    source_ref="costs",
                    source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                    collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                    coverage=SourceCoverage.COMPLETE,
                    freshness=FreshnessStatus.CURRENT,
                    evidence_refs=["evidence:costs"],
                ),
            ],
            attribution_window_days=7,
            fx_basis="provider_daily_close",
        )


def test_reporting_window_uses_local_timezone_boundaries_across_dst() -> None:
    window = reporting_window_for_local_day(date(2026, 3, 29), "Europe/Amsterdam")

    assert window.timezone == "Europe/Amsterdam"
    assert window.start_utc == datetime(2026, 3, 28, 23, 0, tzinfo=timezone.utc)
    assert window.end_utc == datetime(2026, 3, 29, 22, 0, tzinfo=timezone.utc)
    assert window.duration_hours == 23


def test_source_precedence_selects_preferred_component() -> None:
    manual = _component(ComponentKind.COGS, 4_500, source_ref="operator:manual_estimate")
    connector = _component(ComponentKind.COGS, 4_200, source_ref="connector:cost_records")

    chosen = choose_preferred_component(
        [manual, connector],
        source_precedence=["connector:cost_records", "operator:manual_estimate"],
    )

    assert chosen is connector
