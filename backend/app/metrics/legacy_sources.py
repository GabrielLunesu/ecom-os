"""Degraded legacy commerce sources for A08 metrics.

This bridge exists until A04 exposes normalized commerce economics inputs. It feeds
only evidenced, partial components into the deterministic formula layer and leaves
missing cost, fee, ad, and FX inputs visible as coverage gaps.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol

from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
    reporting_window_for_local_day,
)
from app.metrics.snapshots import MetricSnapshotRequest

_ZERO_DECIMAL_CURRENCIES = {
    "BIF",
    "CLP",
    "DJF",
    "GNF",
    "ISK",
    "JPY",
    "KMF",
    "KRW",
    "PYG",
    "RWF",
    "UGX",
    "VND",
    "VUV",
    "XAF",
    "XOF",
    "XPF",
}


class LegacyShopifyOrdersConnector(Protocol):
    async def list_orders(
        self,
        *,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]: ...


def money_minor_from_decimal_string(value: str, currency: str) -> int:
    scale = 0 if currency.upper() in _ZERO_DECIMAL_CURRENCIES else 2
    multiplier = Decimal(10) ** scale
    minor = (Decimal(value) * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(minor)


class LegacyShopifyOrderSource:
    """Partial net-sales source backed by the legacy Shopify order connector."""

    def __init__(
        self,
        *,
        store_id: str,
        connector: LegacyShopifyOrdersConnector,
        collected_at: Callable[[], datetime] | None = None,
    ) -> None:
        self._store_id = store_id
        self._connector = connector
        self._collected_at = collected_at or (lambda: datetime.now(timezone.utc))

    async def components_for_estimated_contribution_margin(
        self,
        request: MetricSnapshotRequest,
    ) -> list[MetricComponentInput]:
        if request.store_id != self._store_id:
            raise ValueError("legacy Shopify source store does not match metric request store")

        window = reporting_window_for_local_day(
            request.reporting_date,
            request.reporting_timezone,
        )
        orders = await self._connector.list_orders(
            created_at_min=window.start_utc.isoformat(),
            created_at_max=window.end_utc.isoformat(),
            limit=250,
        )

        total_minor = 0
        evidence_refs: list[str] = []
        latest_source_timestamp: datetime | None = None

        for order in orders:
            if not _is_net_sales_order(order):
                continue
            order_currency = _order_currency(order)
            if order_currency != request.currency.upper():
                raise ValueError(
                    "legacy Shopify order currency mismatch; normalized FX input is required"
                )
            total_minor += money_minor_from_decimal_string(
                str(order.get("total_price", "0")),
                request.currency,
            )
            evidence_ref = _order_evidence_ref(order)
            if evidence_ref is not None:
                evidence_refs.append(evidence_ref)
            source_timestamp = _parse_order_timestamp(order)
            if source_timestamp is not None and (
                latest_source_timestamp is None or source_timestamp > latest_source_timestamp
            ):
                latest_source_timestamp = source_timestamp

        return [
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=total_minor, currency=request.currency),
                source_ref=f"legacy_shopify_orders:{self._store_id}",
                source_timestamp=latest_source_timestamp or window.end_utc,
                collected_at=_ensure_aware_utc(self._collected_at()),
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=evidence_refs,
            )
        ]


def _is_net_sales_order(order: dict[str, Any]) -> bool:
    status = order.get("financial_status")
    return status in {None, "paid", "partially_refunded"}


def _order_currency(order: dict[str, Any]) -> str:
    currency = order.get("currency") or order.get("presentment_currency")
    if not isinstance(currency, str) or len(currency) != 3:
        raise ValueError("legacy Shopify order is missing ISO currency")
    return currency.upper()


def _order_evidence_ref(order: dict[str, Any]) -> str | None:
    order_id = order.get("id") or order.get("name")
    if order_id is None:
        return None
    return f"shopify_order:{order_id}"


def _parse_order_timestamp(order: dict[str, Any]) -> datetime | None:
    raw_timestamp = order.get("created_at")
    if not isinstance(raw_timestamp, str):
        return None
    return _ensure_aware_utc(datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00")))


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("metric source timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
