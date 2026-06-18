"""Durable inbox stand-in for the A02 event port.

Inbound provider events are persisted BEFORE any processing, and a unique
``(source, account_ref, source_event_id)`` guarantees a duplicate delivery is
accepted exactly once (AGENTS.md §4, I-07). This implements the
:class:`DurableInboxPort` contract A04 consumes from A02; until A02 lands, the
local table backs it (see INTERFACES.md IR-A04-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connectors.models import CommerceProviderEvent


@dataclass(frozen=True)
class InboundEvent:
    """A verified provider event envelope ready for durable insertion."""

    source: str
    source_event_id: str
    account_ref: str
    topic: str
    payload_hash: str
    verification: str
    occurred_at: datetime | None
    brand_id: UUID | None = None
    store_id: UUID | None = None
    connection_id: UUID | None = None
    raw_ref: str = ""


class DurableInboxPort(Protocol):
    """The inbox contract A04 consumes from A02."""

    async def accept(self, event: InboundEvent) -> tuple[CommerceProviderEvent, bool]:
        """Persist the event; return ``(row, is_duplicate)``. Idempotent."""
        ...


class LocalDurableInbox:
    """Postgres/SQLite-backed durable inbox (A02 stand-in)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _find(
        self, source: str, account_ref: str, source_event_id: str
    ) -> CommerceProviderEvent | None:
        result = await self._session.exec(
            select(CommerceProviderEvent).where(
                CommerceProviderEvent.source == source,
                CommerceProviderEvent.account_ref == account_ref,
                CommerceProviderEvent.source_event_id == source_event_id,
            )
        )
        return result.first()

    async def accept(self, event: InboundEvent) -> tuple[CommerceProviderEvent, bool]:
        existing = await self._find(event.source, event.account_ref, event.source_event_id)
        if existing is not None:
            return existing, True

        row = CommerceProviderEvent(
            brand_id=event.brand_id,
            store_id=event.store_id,
            connection_id=event.connection_id,
            source=event.source,
            source_event_id=event.source_event_id,
            account_ref=event.account_ref,
            topic=event.topic,
            payload_hash=event.payload_hash,
            verification=event.verification,
            occurred_at=event.occurred_at,
            raw_ref=event.raw_ref,
        )
        try:
            # SAVEPOINT so a concurrent duplicate rolls back only this insert, not the
            # surrounding transaction (handles the webhook race in AGENTS.md §4).
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            existing = await self._find(event.source, event.account_ref, event.source_event_id)
            if existing is None:  # pragma: no cover - defensive
                raise
            return existing, True
        return row, False

    async def mark_processed(self, event_id: UUID, state: str = "processed") -> None:
        row = await self._session.get(CommerceProviderEvent, event_id)
        if row is not None:
            row.processing_state = state
            self._session.add(row)
            await self._session.flush()
