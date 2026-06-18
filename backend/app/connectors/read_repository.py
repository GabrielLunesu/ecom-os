"""Evidence-backed read access to the normalized commerce model.

Every read returns a :class:`ReadResult` carrying freshness, coverage, and evidence
(BUILD §4, 04-DATA §7/§9). During a connector outage the repository returns the
last-good rows marked ``stale`` rather than fabricating current data (05-OPS §11.2):
the caller can still answer, but the staleness is explicit.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connectors.models import Connection, Customer, Fulfillment, Order, OrderLine, ProviderRef
from app.connectors.ports import Coverage, Evidence, Freshness, ReadResult, payload_hash
from app.core.time import utcnow


class CommerceReadRepository:
    """Read side over the normalized model, with provenance on every result."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        stale_after: timedelta = timedelta(minutes=15),
    ) -> None:
        self._session = session
        self._stale_after = stale_after

    async def store_degraded(self, store_id: UUID) -> bool:
        """A store is degraded if it has no healthy ``store`` connection."""
        conns = (
            await self._session.exec(
                select(Connection).where(
                    Connection.store_id == store_id, Connection.capability == "store"
                )
            )
        ).all()
        if not conns:
            return True
        return not any(c.status in ("connected", "active") and c.last_health_ok for c in conns)

    def _freshness(self, synced_at: Any, *, degraded: bool, partial: bool = False) -> Freshness:
        return Freshness.from_sync(
            synced_at,
            now=utcnow(),
            stale_after=self._stale_after,
            degraded=degraded,
            partial=partial,
        )

    async def _order_evidence(self, order: Order) -> list[Evidence]:
        ref = (
            await self._session.exec(
                select(ProviderRef).where(
                    ProviderRef.entity_type == "order",
                    ProviderRef.entity_id == order.id,
                    ProviderRef.source == order.source,
                )
            )
        ).first()
        reference = (
            f"{order.source}:order:{ref.external_id}"
            if ref
            else f"{order.source}:order:{order.external_id}"
        )
        return [
            Evidence(
                source=order.source,
                source_id=order.external_id,
                source_timestamp=order.source_updated_at,
                collected_timestamp=order.synced_at,
                trust_label="untrusted",
                content_hash=payload_hash(order.to_view()),
                reference=reference,
            )
        ]

    async def _attach_children(self, order: Order) -> dict[str, Any]:
        view = order.to_view()
        lines = (
            await self._session.exec(select(OrderLine).where(OrderLine.order_id == order.id))
        ).all()
        fulfillments = (
            await self._session.exec(select(Fulfillment).where(Fulfillment.order_id == order.id))
        ).all()
        view["lines"] = [li.to_view() for li in lines]
        view["fulfillments"] = [f.to_view() for f in fulfillments]
        return view

    # --- public reads ------------------------------------------------------

    async def get_order(self, store_id: UUID, identifier: str) -> ReadResult[dict[str, Any]] | None:
        """Fetch one order by external id, order number, or internal UUID."""
        order = await self._resolve_order(store_id, identifier)
        if order is None:
            return None
        degraded = await self.store_degraded(store_id)
        view = await self._attach_children(order)
        return ReadResult(
            data=view,
            freshness=self._freshness(order.synced_at, degraded=degraded),
            coverage=_coverage(order.coverage),
            evidence=await self._order_evidence(order),
        )

    async def _resolve_order(self, store_id: UUID, identifier: str) -> Order | None:
        stmt = select(Order).where(Order.store_id == store_id, Order.external_id == identifier)
        order = (await self._session.exec(stmt)).first()
        if order is not None:
            return order
        order = (
            await self._session.exec(
                select(Order).where(Order.store_id == store_id, Order.order_number == identifier)
            )
        ).first()
        if order is not None:
            return order
        try:
            uid = UUID(identifier)
        except (ValueError, AttributeError):
            return None
        candidate = await self._session.get(Order, uid)
        if candidate is not None and candidate.store_id == store_id:
            return candidate
        return None

    async def find_orders_by_customer(
        self, store_id: UUID, email: str
    ) -> ReadResult[list[dict[str, Any]]]:
        """All orders for a customer email, newest source-update first."""
        orders = (
            await self._session.exec(
                select(Order).where(Order.store_id == store_id, Order.email == email)
            )
        ).all()
        orders = sorted(orders, key=lambda o: o.source_updated_at or o.synced_at, reverse=True)
        degraded = await self.store_degraded(store_id)
        evidence: list[Evidence] = []
        views: list[dict[str, Any]] = []
        oldest_sync = None
        for o in orders:
            views.append(await self._attach_children(o))
            evidence.extend(await self._order_evidence(o))
            oldest_sync = o.synced_at if oldest_sync is None else min(oldest_sync, o.synced_at)
        return ReadResult(
            data=views,
            freshness=self._freshness(oldest_sync, degraded=degraded, partial=not orders),
            coverage="imported",
            evidence=evidence,
        )

    async def get_customer(
        self, store_id: UUID, identifier: str
    ) -> ReadResult[dict[str, Any]] | None:
        customer = (
            await self._session.exec(
                select(Customer).where(Customer.store_id == store_id, Customer.email == identifier)
            )
        ).first()
        if customer is None:
            customer = (
                await self._session.exec(
                    select(Customer).where(
                        Customer.store_id == store_id, Customer.external_id == identifier
                    )
                )
            ).first()
        if customer is None:
            return None
        degraded = await self.store_degraded(store_id)
        return ReadResult(
            data=customer.to_view(),
            freshness=self._freshness(customer.synced_at, degraded=degraded),
            coverage=_coverage(customer.coverage),
            evidence=[
                Evidence(
                    source=customer.source,
                    source_id=customer.external_id,
                    source_timestamp=customer.source_updated_at,
                    collected_timestamp=customer.synced_at,
                    trust_label="untrusted",
                    content_hash=payload_hash(customer.to_view()),
                    reference=f"{customer.source}:customer:{customer.external_id}",
                )
            ],
        )

    async def list_stores(self) -> ReadResult[list[dict[str, Any]]]:
        conns = (await self._session.exec(select(Connection))).all()
        by_store: dict[UUID, list[Connection]] = {}
        for c in conns:
            by_store.setdefault(c.store_id, []).append(c)
        stores = [
            {
                "store_id": str(store_id),
                "connections": [
                    {
                        "connection_id": str(c.id),
                        "provider": c.provider,
                        "capability": c.capability,
                        "status": c.status,
                        "healthy": c.last_health_ok,
                        "last_health_at": (
                            c.last_health_at.isoformat() if c.last_health_at else None
                        ),
                    }
                    for c in cs
                ],
            }
            for store_id, cs in by_store.items()
        ]
        return ReadResult(
            data=stores,
            freshness=Freshness(as_of=utcnow(), status="current"),
            coverage="verified",
            evidence=[],
        )


def _coverage(value: str) -> Coverage:
    if value in ("verified", "observed", "imported", "unknown"):
        return value  # type: ignore[return-value]
    return "unknown"
