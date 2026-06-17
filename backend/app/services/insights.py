"""Reflection jobs: compute anomalies/alerts from live data (Build Spec §8.12).

Deterministic v1: delivery-window anomaly, refund-risk, ticket-spike, and a CS
health summary. Regenerated on demand (and schedulable via the runtime/cron).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.insight import Insight
from app.models.refunds import RefundRequest
from app.models.tickets import Ticket
from app.services.connectors.registry import shopify_connector_for
from app.services.connectors.secrets import ConnectionRef
from app.services.stores import list_stores

_STALE_FULFILL_DAYS = 7
_TICKET_SPIKE_THRESHOLD = 5


def _parse(dt: str) -> datetime | None:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


async def generate_insights(session: AsyncSession, brand: Brand) -> list[Insight]:
    """Recompute insights from current data, replacing the previous set."""
    # Clear prior insights (fresh snapshot each run).
    for old in (await session.exec(select(Insight).where(Insight.brand_id == brand.id))).all():
        await session.delete(old)
    await session.commit()

    out: list[Insight] = []
    now = utcnow().replace(tzinfo=timezone.utc)

    # 1. Delivery-window anomaly: unfulfilled orders older than the window.
    stores = await list_stores(session)
    stale = 0
    if stores:
        conn = shopify_connector_for(
            ConnectionRef(provider=stores[0].provider, external_id=stores[0].external_id)
        )
        try:
            since = (now - timedelta(days=30)).isoformat()
            orders = await conn.list_orders(created_at_min=since)
        except Exception:  # noqa: BLE001
            orders = []
        cutoff = now - timedelta(days=_STALE_FULFILL_DAYS)
        for o in orders:
            if not o.get("fulfillment_status"):
                created = _parse(o.get("created_at", ""))
                if created and created < cutoff:
                    stale += 1
    out.append(
        Insight(
            brand_id=brand.id,
            kind="delivery_window",
            severity="warning" if stale else "info",
            title=f"{stale} order(s) unfulfilled > {_STALE_FULFILL_DAYS} days"
            if stale
            else "Fulfillment on track",
            detail="Investigate carrier delays and update tracking."
            if stale
            else "No orders are stuck beyond the delivery window.",
            data={"stale_orders": stale},
        )
    )

    # 2. Refund-risk: pending/failed refund requests.
    refunds = (await session.exec(select(RefundRequest))).all()
    at_risk = [r for r in refunds if r.status in ("pending", "failed")]
    out.append(
        Insight(
            brand_id=brand.id,
            kind="refund_risk",
            severity="warning" if at_risk else "info",
            title=f"{len(at_risk)} refund(s) need attention" if at_risk else "No refund backlog",
            detail="Pending or failed refunds in the approval lane.",
            data={"count": len(at_risk)},
        )
    )

    # 3. Ticket-spike + CS health.
    tickets = (await session.exec(select(Ticket))).all()
    week_ago = now - timedelta(days=7)
    recent = [t for t in tickets if (t.created_at.replace(tzinfo=timezone.utc) >= week_ago)]
    resolved = [t for t in tickets if t.status == "resolved"]
    needs_rep = [t for t in tickets if t.status == "needs_rep"]
    spike = len(recent) >= _TICKET_SPIKE_THRESHOLD
    out.append(
        Insight(
            brand_id=brand.id,
            kind="ticket_spike",
            severity="warning" if spike else "info",
            title=f"Ticket spike: {len(recent)} this week" if spike else f"{len(recent)} tickets this week",
            detail=f"{len(resolved)} auto-resolved, {len(needs_rep)} awaiting a rep.",
            data={"week": len(recent), "resolved": len(resolved), "needs_rep": len(needs_rep)},
        )
    )

    for ins in out:
        session.add(ins)
    await session.commit()
    for ins in out:
        await session.refresh(ins)
    return out


async def list_insights(session: AsyncSession) -> list[Insight]:
    return list(
        (await session.exec(select(Insight).order_by(Insight.created_at.desc()))).all()  # type: ignore[attr-defined]
    )
