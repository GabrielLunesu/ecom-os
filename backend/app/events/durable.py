"""Durable inbox and transactional outbox primitives."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.events import DurableInboxEvent, DurableOutboxEvent

VALID_COVERAGE = {"verified", "observed", "imported", "unknown"}
VALID_VERIFICATION = {"valid", "invalid", "not_required"}


class InboxVerificationError(ValueError):
    """Raised when an inbound event cannot be durably accepted."""


class OutboxLeaseError(RuntimeError):
    """Raised when a worker no longer owns an outbox event lease."""


def payload_hash(payload: dict[str, Any] | list[Any] | str | bytes) -> str:
    """Return a stable SHA-256 hash for a provider payload."""

    if isinstance(payload, bytes):
        data = payload
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


async def accept_inbox_event(
    session: AsyncSession,
    *,
    event_type: str,
    source: str,
    source_event_id: str,
    payload: dict[str, Any],
    source_scope: str = "",
    schema_version: int = 1,
    brand_id: UUID | None = None,
    store_id: UUID | None = None,
    connection_id: UUID | None = None,
    trace_id: UUID | None = None,
    causation_event_id: UUID | None = None,
    correlation_key: str | None = None,
    occurred_at: datetime | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    coverage: str = "imported",
    verification: str = "valid",
    metadata: dict[str, Any] | None = None,
) -> tuple[DurableInboxEvent, bool]:
    """Create or reuse a durable inbox event.

    Returns `(event, created)`. Duplicate provider events are recognized by
    `(source, source_scope, source_event_id)` and return the already accepted row.
    """

    if verification != "valid":
        raise InboxVerificationError("inbound event verification must be valid before acceptance")
    if coverage not in VALID_COVERAGE:
        raise ValueError(f"unsupported coverage={coverage!r}")
    if verification not in VALID_VERIFICATION:
        raise ValueError(f"unsupported verification={verification!r}")

    existing = (
        await session.exec(
            select(DurableInboxEvent)
            .where(DurableInboxEvent.source == source)
            .where(DurableInboxEvent.source_scope == source_scope)
            .where(DurableInboxEvent.source_event_id == source_event_id)
        )
    ).first()
    if existing is not None:
        return existing, False

    event = DurableInboxEvent(
        event_type=event_type,
        schema_version=schema_version,
        source=source,
        source_scope=source_scope,
        source_event_id=source_event_id,
        brand_id=brand_id,
        store_id=store_id,
        connection_id=connection_id,
        trace_id=trace_id,
        causation_event_id=causation_event_id,
        correlation_key=correlation_key,
        occurred_at=occurred_at,
        received_at=utcnow(),
        actor_type=actor_type,
        actor_id=actor_id,
        coverage=coverage,
        payload_hash=payload_hash(payload),
        verification=verification,
        data=payload,
        event_metadata=metadata or {},
    )
    session.add(event)
    await session.flush()
    return event, True


async def enqueue_outbox_event(
    session: AsyncSession,
    *,
    topic: str,
    payload: dict[str, Any],
    deduplication_key: str,
    trace_id: UUID | None = None,
    schema_version: int = 1,
    max_attempts: int = 5,
) -> tuple[DurableOutboxEvent, bool]:
    """Create or reuse an outbox row by deduplication key."""

    existing = (
        await session.exec(
            select(DurableOutboxEvent).where(
                DurableOutboxEvent.deduplication_key == deduplication_key
            )
        )
    ).first()
    if existing is not None:
        return existing, False

    event = DurableOutboxEvent(
        topic=topic,
        schema_version=schema_version,
        payload=payload,
        deduplication_key=deduplication_key,
        trace_id=trace_id,
        max_attempts=max_attempts,
    )
    session.add(event)
    await session.flush()
    return event, True


async def claim_outbox_events(
    session: AsyncSession,
    *,
    worker_id: str,
    topic: str | None = None,
    limit: int = 10,
    lease_seconds: int = 60,
) -> list[DurableOutboxEvent]:
    """Claim runnable outbox events for one dispatcher worker.

    The state transition is the durable boundary that prevents duplicate
    dispatch. PostgreSQL row locking can be layered on by the dispatcher; the
    SQLite-backed invariant tests still exercise lease/reclaim semantics.
    """

    now = utcnow()
    statement = (
        select(DurableOutboxEvent)
        .where(col(DurableOutboxEvent.state).in_(["pending", "leased"]))
        .where(DurableOutboxEvent.next_run_at <= now)
        .order_by(col(DurableOutboxEvent.created_at))
    )
    if topic is not None:
        statement = statement.where(DurableOutboxEvent.topic == topic)

    claimed: list[DurableOutboxEvent] = []
    for event in (await session.exec(statement)).all():
        if len(claimed) >= limit:
            break
        if (
            event.state == "leased"
            and event.lease_expires_at is not None
            and event.lease_expires_at > now
        ):
            continue
        event.state = "leased"
        event.lease_owner = worker_id
        event.lease_expires_at = now + timedelta(seconds=lease_seconds)
        event.attempts += 1
        event.updated_at = now
        session.add(event)
        claimed.append(event)

    await session.flush()
    return claimed


def _assert_outbox_owner(event: DurableOutboxEvent, worker_id: str) -> None:
    if event.state != "leased" or event.lease_owner != worker_id:
        raise OutboxLeaseError("worker does not own the active outbox lease")


async def mark_outbox_delivered(
    session: AsyncSession,
    event: DurableOutboxEvent,
    *,
    worker_id: str,
) -> DurableOutboxEvent:
    """Mark an outbox event as delivered."""

    _assert_outbox_owner(event, worker_id)
    now = utcnow()
    event.state = "delivered"
    event.delivered_at = now
    event.lease_owner = None
    event.lease_expires_at = None
    event.updated_at = now
    session.add(event)
    await session.flush()
    return event


async def mark_outbox_failed(
    session: AsyncSession,
    event: DurableOutboxEvent,
    *,
    error: str,
    worker_id: str,
    retry_at: datetime | None = None,
) -> DurableOutboxEvent:
    """Record a failed outbox delivery attempt with bounded retry state."""

    _assert_outbox_owner(event, worker_id)
    now = utcnow()
    event.last_error = error
    event.lease_owner = None
    event.lease_expires_at = None
    event.updated_at = now
    if event.attempts >= event.max_attempts:
        event.state = "dead_letter"
    else:
        event.state = "pending"
        event.next_run_at = retry_at or now
    session.add(event)
    await session.flush()
    return event
