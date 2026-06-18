"""Direct-Shopify adapter: normalizes raw Admin payloads behind the v2 port.

Reuses the prototype :class:`DirectShopifyConnector` for transport but converts raw
Shopify dicts into the normalized domain shape so provider payloads never cross the
connector boundary (AGENTS.md §10). Reads (the WISMO path) are implemented and
verifiable against normalization fixtures. Writes are intentionally declared
unsupported here until a live-conformance fixture exists (AGENTS.md §8: a direct
connector must "provide reconciliation or declare the limitation visibly"); the
durable write/reconcile vertical is exercised end-to-end via the fake adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import (
    CapabilityUnsupported,
    ConnectorUnavailable,
    ProviderPayloadError,
)
from app.connectors.ports import (
    CapabilityDescriptor,
    ConnectorPort,
    to_minor_units,
)
from app.services.connectors.secrets import ConnectionRef
from app.services.connectors.shopify_direct import DirectShopifyConnector

ADAPTER_VERSION = "shopify-direct-2025-01"
SOURCE = "shopify"


def _parse_dt(value: str | None) -> datetime | None:
    """Parse a Shopify ISO-8601 timestamp into naive UTC, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def normalize_order(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw Shopify order into the normalized domain shape."""
    if "id" not in raw:
        raise ProviderPayloadError("shopify order payload missing id")
    currency = raw.get("currency") or "USD"
    customer_raw = raw.get("customer") or {}
    customer = None
    if customer_raw.get("id"):
        customer = {
            "external_id": str(customer_raw.get("id")),
            "email": customer_raw.get("email", "") or raw.get("email", ""),
            "name": " ".join(
                p for p in [customer_raw.get("first_name"), customer_raw.get("last_name")] if p
            ).strip(),
            "orders_count": int(customer_raw.get("orders_count", 0) or 0),
            "source_updated_at": _parse_dt(customer_raw.get("updated_at")),
        }
    lines = [
        {
            "external_id": str(li.get("id", "")),
            "title": li.get("title", ""),
            "sku": li.get("sku", "") or "",
            "quantity": int(li.get("quantity", 0) or 0),
            "price_minor": to_minor_units(li.get("price")),
            "product_external_id": str(li.get("product_id", "") or ""),
        }
        for li in raw.get("line_items", [])
    ]
    fulfillments = [normalize_fulfillment(f) for f in raw.get("fulfillments", [])]
    return {
        "external_id": str(raw["id"]),
        "order_number": raw.get("name", "") or "",
        "email": raw.get("email", "") or "",
        "currency": currency,
        "total_minor": to_minor_units(raw.get("total_price")),
        "subtotal_minor": to_minor_units(raw.get("subtotal_price")),
        "financial_status": raw.get("financial_status", "") or "",
        "fulfillment_status": raw.get("fulfillment_status", "") or "",
        "placed_at": _parse_dt(raw.get("created_at")),
        "source_updated_at": _parse_dt(raw.get("updated_at")),
        "customer": customer,
        "lines": lines,
        "fulfillments": fulfillments,
    }


def normalize_fulfillment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw.get("id", "")),
        "status": raw.get("status", "") or "",
        "tracking_company": raw.get("tracking_company", "") or "",
        "tracking_number": (raw.get("tracking_numbers") or [raw.get("tracking_number")] or [""])[0]
        or "",
        "tracking_url": (raw.get("tracking_urls") or [raw.get("tracking_url")] or [""])[0] or "",
        "shipped_at": _parse_dt(raw.get("created_at")),
        "source_updated_at": _parse_dt(raw.get("updated_at")),
    }


class ShopifyCommerceAdapter(ConnectorPort):
    """Normalized read surface over one store's direct Shopify connection."""

    def __init__(self, binding: ConnectionBinding) -> None:
        super().__init__(binding)
        # account_ref is the (non-secret) store domain for direct Shopify.
        self._connector = DirectShopifyConnector(
            ConnectionRef(provider="direct", external_id=binding.account_ref)
        )
        self.descriptor = CapabilityDescriptor(
            provider=binding.provider,
            capability="store",
            read_operations=("orders",),
            write_operations=(),
            supports_idempotency=False,
            supports_reconciliation=False,
            sandbox=False,
        )

    async def health(self) -> dict[str, Any]:
        try:
            shop = await self._connector.get_shop()
        except Exception as exc:  # noqa: BLE001 - classify transport failures
            raise ConnectorUnavailable("shopify shop probe failed") from exc
        return {
            "provider": "shopify",
            "account_ref": self.binding.account_ref,
            "name": shop.get("name", ""),
            "status": "ACTIVE",
        }

    async def fetch(
        self, resource: str, *, cursor: str | None = None, limit: int = 250
    ) -> tuple[list[dict[str, Any]], str | None]:
        if resource != "orders":
            raise CapabilityUnsupported(f"shopify adapter cannot fetch {resource!r}")
        try:
            raw_orders = await self._connector.list_orders(
                created_at_min=cursor or None, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise ConnectorUnavailable("shopify list_orders failed") from exc
        return [normalize_order(o) for o in raw_orders], None

    async def fetch_one(self, resource: str, external_id: str) -> dict[str, Any] | None:
        if resource != "orders":
            raise CapabilityUnsupported(f"shopify adapter cannot fetch {resource!r}")
        try:
            raw = await self._connector.get_order(external_id)
        except Exception as exc:  # noqa: BLE001
            raise ConnectorUnavailable("shopify get_order failed") from exc
        if not raw:
            return None
        # Merge fulfillments fetched separately so WISMO tracking is present.
        try:
            fulfillments = await self._connector.get_fulfillments(external_id)
            raw.setdefault("fulfillments", fulfillments)
        except Exception:  # noqa: BLE001 - fulfillments are best-effort enrichment
            pass
        return normalize_order(raw)
