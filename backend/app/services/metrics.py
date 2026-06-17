"""Store KPI computation from Shopify orders (Build Spec §7.1).

Order-derived KPIs (revenue, orders, AOV) are computed from the Orders API.
Session-based KPIs (sessions, conversion, ATC rate) require Shopify's Analytics
(`read_reports`), which this connection lacks — they are returned as `null` with a
reason so the UI degrades gracefully instead of showing wrong numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Store
from app.services.connectors.secrets import ConnectionRef
from app.services.connectors.registry import shopify_connector_for
from app.services.stores import list_stores

# KPIs we cannot compute without read_reports; surfaced as unavailable.
UNAVAILABLE_REASON = "requires Shopify Analytics (read_reports) — not granted"


@dataclass
class StoreKpis:
    store_id: str
    store_name: str
    revenue: float
    orders: int
    aov: float
    currency: str
    # Session-based metrics: None when unavailable.
    sessions: int | None
    conversion: float | None
    atc_rate: float | None


def _kpis_from_orders(
    store_id: str, store_name: str, orders: list[dict[str, Any]]
) -> StoreKpis:
    paid = [o for o in orders if o.get("financial_status") in (None, "paid", "partially_refunded")]
    revenue = sum(float(o.get("total_price") or 0) for o in paid)
    count = len(paid)
    currency = (orders[0].get("currency") if orders else None) or "USD"
    return StoreKpis(
        store_id=store_id,
        store_name=store_name,
        revenue=round(revenue, 2),
        orders=count,
        aov=round(revenue / count, 2) if count else 0.0,
        currency=currency,
        sessions=None,
        conversion=None,
        atc_rate=None,
    )


async def _store_kpis(store: Store, days: int) -> StoreKpis:
    ref = ConnectionRef(provider=store.provider, external_id=store.external_id)
    conn = shopify_connector_for(ref)
    since = (utcnow() - timedelta(days=days)).isoformat()
    orders = await conn.list_orders(created_at_min=since)
    return _kpis_from_orders(str(store.id), store.name, orders)


async def store_metrics(
    session: AsyncSession, *, store_id: str | None, days: int
) -> dict[str, object]:
    """Compute KPIs for one store, or the aggregate across all stores.

    store_id None / "all" -> aggregate. Returns a structure with the scope's KPIs
    plus a per-store breakdown and an `unavailable` note for session metrics.
    """
    stores = await list_stores(session)
    if store_id and store_id != "all":
        stores = [s for s in stores if str(s.id) == store_id]

    per_store = [await _store_kpis(s, days) for s in stores]

    revenue = round(sum(k.revenue for k in per_store), 2)
    orders = sum(k.orders for k in per_store)
    currency = per_store[0].currency if per_store else "USD"
    aggregate = {
        "revenue": revenue,
        "orders": orders,
        "aov": round(revenue / orders, 2) if orders else 0.0,
        "currency": currency,
        "sessions": None,
        "conversion": None,
        "atc_rate": None,
    }
    return {
        "scope": store_id or "all",
        "days": days,
        "kpis": aggregate,
        "per_store": [k.__dict__ for k in per_store],
        "unavailable": {
            "sessions": UNAVAILABLE_REASON,
            "conversion": UNAVAILABLE_REASON,
            "atc_rate": UNAVAILABLE_REASON,
        },
    }
