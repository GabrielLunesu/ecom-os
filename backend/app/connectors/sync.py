"""Initial and incremental synchronization into the normalized read model.

Upserts are idempotent on the natural key ``(store_id, source, external_id)`` so a
re-run, a duplicate webhook, or a racing worker changes normalized state exactly once
(I-07). Each upsert records ``source``, the opaque ``external_id`` (kept separate in a
:class:`ProviderRef`), ``source_updated_at``, and ``synced_at`` (BUILD §4).

The sync layer never persists raw provider payloads — it consumes the *normalized*
records returned by :class:`ConnectorPort` and maps them onto rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connectors.binding import ConnectionBinding
from app.connectors.models import (
    Customer,
    Fulfillment,
    Order,
    OrderLine,
    Product,
    ProviderRef,
    SyncCursor,
)
from app.connectors.ports import ConnectorPort
from app.core.time import utcnow


@dataclass(frozen=True)
class SyncReport:
    resource: str
    processed: int
    created: int
    updated: int
    cursor: str | None


class SyncEngine:
    """Maps a connector's normalized records into the durable read model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- upserts -----------------------------------------------------------

    async def _upsert_provider_ref(
        self,
        entity_type: str,
        entity_id: UUID,
        *,
        source: str,
        external_id: str,
        external_version: str,
        connection_id: UUID | None,
    ) -> None:
        existing = (
            await self._session.exec(
                select(ProviderRef).where(
                    ProviderRef.entity_type == entity_type,
                    ProviderRef.entity_id == entity_id,
                    ProviderRef.source == source,
                )
            )
        ).first()
        if existing is None:
            self._session.add(
                ProviderRef(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    source=source,
                    external_id=external_id,
                    external_version=external_version,
                    connection_id=connection_id,
                )
            )
        else:
            existing.external_version = external_version
            self._session.add(existing)

    async def upsert_customer(
        self, store_id: UUID, source: str, data: dict[str, Any], connection_id: UUID | None
    ) -> Customer | None:
        if not data:
            return None
        ext = str(data.get("external_id") or "")
        if not ext:
            return None
        row = (
            await self._session.exec(
                select(Customer).where(
                    Customer.store_id == store_id,
                    Customer.source == source,
                    Customer.external_id == ext,
                )
            )
        ).first()
        if row is None:
            row = Customer(store_id=store_id, source=source, external_id=ext)
        row.email = data.get("email", row.email) or row.email
        row.name = data.get("name", row.name) or row.name
        row.orders_count = int(data.get("orders_count", row.orders_count) or 0)
        row.source_updated_at = data.get("source_updated_at") or row.source_updated_at
        row.synced_at = utcnow()
        row.coverage = "imported"
        self._session.add(row)
        await self._session.flush()
        await self._upsert_provider_ref(
            "customer",
            row.id,
            source=source,
            external_id=ext,
            external_version=_version(row.source_updated_at),
            connection_id=connection_id,
        )
        return row

    async def upsert_order(
        self, store_id: UUID, source: str, data: dict[str, Any], connection_id: UUID | None
    ) -> tuple[Order, bool]:
        """Idempotent upsert of one normalized order (+customer/lines/fulfilments)."""
        ext = str(data["external_id"])
        customer = await self.upsert_customer(
            store_id, source, data.get("customer") or {}, connection_id
        )
        row = (
            await self._session.exec(
                select(Order).where(
                    Order.store_id == store_id,
                    Order.source == source,
                    Order.external_id == ext,
                )
            )
        ).first()
        created = row is None
        if row is None:
            row = Order(store_id=store_id, source=source, external_id=ext)
        row.customer_id = customer.id if customer else row.customer_id
        row.order_number = data.get("order_number", row.order_number) or row.order_number
        row.email = data.get("email", row.email) or row.email
        row.currency = data.get("currency", row.currency) or row.currency
        row.total_minor = int(data.get("total_minor", row.total_minor) or 0)
        row.subtotal_minor = int(data.get("subtotal_minor", row.subtotal_minor) or 0)
        row.financial_status = data.get("financial_status", row.financial_status) or ""
        row.fulfillment_status = data.get("fulfillment_status", row.fulfillment_status) or ""
        row.placed_at = data.get("placed_at") or row.placed_at
        row.source_updated_at = data.get("source_updated_at") or row.source_updated_at
        row.synced_at = utcnow()
        row.coverage = "imported"
        self._session.add(row)
        await self._session.flush()

        await self._upsert_lines(row.id, data.get("lines") or [])
        await self._upsert_fulfillments(row.id, source, data.get("fulfillments") or [])
        await self._upsert_provider_ref(
            "order",
            row.id,
            source=source,
            external_id=ext,
            external_version=_version(row.source_updated_at),
            connection_id=connection_id,
        )
        return row, created

    async def _upsert_lines(self, order_id: UUID, lines: list[dict[str, Any]]) -> None:
        for li in lines:
            ext = str(li.get("external_id") or "")
            row = (
                await self._session.exec(
                    select(OrderLine).where(
                        OrderLine.order_id == order_id, OrderLine.external_id == ext
                    )
                )
            ).first()
            if row is None:
                row = OrderLine(order_id=order_id, external_id=ext)
            row.title = li.get("title", "") or ""
            row.sku = li.get("sku", "") or ""
            row.quantity = int(li.get("quantity", 0) or 0)
            row.price_minor = int(li.get("price_minor", 0) or 0)
            row.product_external_id = str(li.get("product_external_id", "") or "")
            self._session.add(row)
        await self._session.flush()

    async def _upsert_fulfillments(
        self, order_id: UUID, source: str, fulfillments: list[dict[str, Any]]
    ) -> None:
        for f in fulfillments:
            ext = str(f.get("external_id") or "")
            row = (
                await self._session.exec(
                    select(Fulfillment).where(
                        Fulfillment.order_id == order_id,
                        Fulfillment.source == source,
                        Fulfillment.external_id == ext,
                    )
                )
            ).first()
            if row is None:
                row = Fulfillment(order_id=order_id, source=source, external_id=ext)
            row.status = f.get("status", "") or ""
            row.tracking_company = f.get("tracking_company", "") or ""
            row.tracking_number = f.get("tracking_number", "") or ""
            row.tracking_url = f.get("tracking_url", "") or ""
            row.shipped_at = f.get("shipped_at") or row.shipped_at
            row.source_updated_at = f.get("source_updated_at") or row.source_updated_at
            row.synced_at = utcnow()
            self._session.add(row)
        await self._session.flush()

    async def upsert_product(
        self, store_id: UUID, source: str, data: dict[str, Any], connection_id: UUID | None
    ) -> Product:
        ext = str(data["external_id"])
        row = (
            await self._session.exec(
                select(Product).where(
                    Product.store_id == store_id,
                    Product.source == source,
                    Product.external_id == ext,
                )
            )
        ).first()
        if row is None:
            row = Product(store_id=store_id, source=source, external_id=ext)
        row.title = data.get("title", row.title) or row.title
        row.status = data.get("status", row.status) or row.status
        row.source_updated_at = data.get("source_updated_at") or row.source_updated_at
        row.synced_at = utcnow()
        self._session.add(row)
        await self._session.flush()
        await self._upsert_provider_ref(
            "product",
            row.id,
            source=source,
            external_id=ext,
            external_version=_version(row.source_updated_at),
            connection_id=connection_id,
        )
        return row

    # --- sync drivers ------------------------------------------------------

    async def _save_cursor(
        self, connection_id: UUID, resource: str, cursor: str | None, status: str
    ) -> None:
        row = (
            await self._session.exec(
                select(SyncCursor).where(
                    SyncCursor.connection_id == connection_id, SyncCursor.resource == resource
                )
            )
        ).first()
        if row is None:
            row = SyncCursor(connection_id=connection_id, resource=resource)
        row.cursor = cursor or ""
        row.last_synced_at = utcnow()
        row.last_status = status
        self._session.add(row)
        await self._session.flush()

    async def sync_orders(
        self,
        binding: ConnectionBinding,
        port: ConnectorPort,
        *,
        cursor: str | None = None,
        page_limit: int = 250,
        max_pages: int = 20,
    ) -> SyncReport:
        """Page orders from the connector and upsert them idempotently.

        Used for both initial sync (``cursor=None``) and incremental sync (cursor =
        the source watermark). Re-running is safe: existing orders are updated, not
        duplicated.
        """
        processed = created = updated = 0
        next_cursor = cursor
        for _ in range(max_pages):
            records, next_cursor = await port.fetch("orders", cursor=next_cursor, limit=page_limit)
            for rec in records:
                _, was_created = await self.upsert_order(
                    binding.store_id, _source_for(binding), rec, binding.connection_id
                )
                processed += 1
                created += int(was_created)
                updated += int(not was_created)
            if next_cursor is None:
                break
        await self._save_cursor(binding.connection_id, "orders", next_cursor, "ok")
        return SyncReport("orders", processed, created, updated, next_cursor)

    async def apply_order_event(
        self, binding: ConnectionBinding, port: ConnectorPort, external_id: str
    ) -> Order | None:
        """Fetch one order by id and upsert it (webhook-driven incremental).

        Applying the same provider event twice changes normalized state once.
        """
        rec = await port.fetch_one("orders", external_id)
        if rec is None:
            return None
        row, _ = await self.upsert_order(
            binding.store_id, _source_for(binding), rec, binding.connection_id
        )
        return row


def _source_for(binding: ConnectionBinding) -> str:
    """The canonical source label for a binding's provider."""
    return "shopify" if binding.provider in ("direct", "composio") else binding.provider


def _version(source_updated_at: datetime | None) -> str:
    return source_updated_at.isoformat() if source_updated_at else ""
