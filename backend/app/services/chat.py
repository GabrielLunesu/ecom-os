"""Read-only Chat copilot over Shopify + the vault (Build Spec §7.4).

STRICTLY read-only: this router only ever calls read methods and vault lookups —
it never writes, never creates discounts, never refunds. It is a separate trust
surface from the ticket pipeline (Invariant 4): operator queries here never flow
into autonomous customer-facing actions.
"""

from __future__ import annotations

import re

from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.connectors.registry import shopify_connector_for
from app.services.connectors.secrets import ConnectionRef
from app.services.metrics import store_metrics
from app.services.stores import list_stores
from app.services.vault import search as vault_search

_ORDER_RE = re.compile(r"#?\s*(\d{3,})")
_KPI_WORDS = ("revenue", "sales", "kpi", "kpis", "orders", "aov", "metric", "how much")


async def answer(session: AsyncSession, message: str) -> dict[str, object]:
    text = (message or "").lower().strip()
    sources: list[dict[str, str]] = []

    # 1. Order lookup.
    if "order" in text or _ORDER_RE.search(text):
        m = _ORDER_RE.search(text)
        if m:
            stores = await list_stores(session)
            if stores:
                conn = shopify_connector_for(
                    ConnectionRef(provider=stores[0].provider, external_id=stores[0].external_id)
                )
                try:
                    results = await conn.search_orders(f"#{m.group(1)}", limit=1)
                except Exception:  # noqa: BLE001
                    results = []
                if results:
                    o = results[0]
                    sources.append({"type": "shopify_order", "ref": str(o.get("name", ""))})
                    status = o.get("fulfillment_status") or "unfulfilled"
                    return {
                        "answer": (
                            f"Order {o.get('name')} — total {o.get('total_price')} "
                            f"{o.get('currency', '')}, fulfillment: {status}, "
                            f"financial: {o.get('financial_status')}."
                        ),
                        "sources": sources,
                    }
                return {"answer": f"I couldn't find order #{m.group(1)}.", "sources": sources}

    # 2. KPIs.
    if any(w in text for w in _KPI_WORDS):
        metrics = await store_metrics(session, store_id="all", days=30)
        k: dict[str, object] = metrics["kpis"]  # type: ignore[assignment]
        sources.append({"type": "shopify_metrics", "ref": "last 30 days"})
        return {
            "answer": (
                f"Last 30 days across all stores: revenue ${k['revenue']}, "
                f"{k['orders']} orders, AOV ${k['aov']}. "
                "Session/conversion metrics need Shopify Analytics (read_reports)."
            ),
            "sources": sources,
        }

    # 3. Vault search — try the whole message, then significant keywords.
    docs = await vault_search(session, message, limit=2)
    if not docs:
        for word in sorted(set(re.findall(r"[a-zA-Z]{4,}", text)), key=len, reverse=True):
            docs = await vault_search(session, word, limit=2)
            if docs:
                break
    if docs:
        for d in docs:
            sources.append({"type": "vault", "ref": d.slug})
        top = docs[0]
        excerpt = " ".join(top.body.split())[:400]
        return {"answer": f"From “{top.title}”: {excerpt}…", "sources": sources}

    return {
        "answer": (
            "I'm a read-only copilot. Ask me to look up an order (e.g. \"order #1001\"), "
            "report KPIs (\"revenue last 30 days\"), or search the brand vault."
        ),
        "sources": sources,
    }
