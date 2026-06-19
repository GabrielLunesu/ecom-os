from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest

from app.metrics.formulas import ComponentKind, FreshnessStatus, SourceCoverage
from app.metrics.legacy_sources import LegacyShopifyOrderSource, money_minor_from_decimal_string
from app.metrics.snapshots import (
    MetricSnapshotRequest,
    generate_estimated_contribution_margin_snapshot,
)


class _FakeConnector:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def list_orders(
        self,
        *,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "created_at_min": created_at_min,
                "created_at_max": created_at_max,
                "limit": limit,
            }
        )
        return [
            {
                "id": 1001,
                "name": "#1001",
                "total_price": "12.34",
                "currency": "USD",
                "financial_status": "paid",
                "created_at": "2026-06-17T10:30:00Z",
            },
            {
                "id": 1002,
                "name": "#1002",
                "total_price": "7.66",
                "currency": "USD",
                "financial_status": "partially_refunded",
                "created_at": "2026-06-17T11:30:00Z",
            },
            {
                "id": 1003,
                "name": "#1003",
                "total_price": "99.00",
                "currency": "USD",
                "financial_status": "voided",
                "created_at": "2026-06-17T12:30:00Z",
            },
        ]


def test_money_minor_from_decimal_string_uses_integer_minor_units() -> None:
    assert money_minor_from_decimal_string("12.34", "USD") == 1234
    assert money_minor_from_decimal_string("12", "USD") == 1200
    assert money_minor_from_decimal_string("1200", "JPY") == 1200


@pytest.mark.asyncio
async def test_legacy_shopify_source_returns_partial_net_sales_component() -> None:
    connector = _FakeConnector()
    source = LegacyShopifyOrderSource(
        store_id="store_legacy",
        connector=connector,
        collected_at=lambda: datetime(2026, 6, 18, 1, 2, tzinfo=timezone.utc),
    )
    request = MetricSnapshotRequest(
        brand_id="brand_1",
        store_id="store_legacy",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="none_legacy_single_currency",
    )

    components = await source.components_for_estimated_contribution_margin(request)

    assert connector.calls == [
        {
            "created_at_min": "2026-06-17T00:00:00+00:00",
            "created_at_max": "2026-06-18T00:00:00+00:00",
            "limit": 250,
        }
    ]
    assert len(components) == 1
    component = components[0]
    assert component.kind == ComponentKind.NET_SALES
    assert component.amount.minor == 2000
    assert component.amount.currency == "USD"
    assert component.coverage == SourceCoverage.PARTIAL
    assert component.freshness == FreshnessStatus.CURRENT
    assert component.source_ref == "legacy_shopify_orders:store_legacy"
    assert component.evidence_refs == ["shopify_order:1001", "shopify_order:1002"]


@pytest.mark.asyncio
async def test_legacy_source_snapshot_keeps_missing_costs_visible() -> None:
    connector = _FakeConnector()
    source = LegacyShopifyOrderSource(
        store_id="store_legacy",
        connector=connector,
        collected_at=lambda: datetime(2026, 6, 18, 1, 2, tzinfo=timezone.utc),
    )
    request = MetricSnapshotRequest(
        brand_id="brand_1",
        store_id="store_legacy",
        reporting_date=date(2026, 6, 17),
        reporting_timezone="UTC",
        currency="USD",
        attribution_window_days=7,
        fx_basis="none_legacy_single_currency",
    )

    snapshot = await generate_estimated_contribution_margin_snapshot(request, source=source)

    assert snapshot.value.minor == 2000
    assert snapshot.coverage == SourceCoverage.PARTIAL
    assert ComponentKind.COGS in snapshot.missing_component_kinds
    assert ComponentKind.PAYMENT_MARKETPLACE_FEES in snapshot.missing_component_kinds
    assert ComponentKind.ATTRIBUTED_AD_SPEND in snapshot.missing_component_kinds
    assert any("Missing contribution components" in warning for warning in snapshot.warnings)
