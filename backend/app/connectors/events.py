"""Normalized inbox/message events for A05.

A04 emits normalized, untrusted-flagged message events; it does NOT decide ticket
workflow, status, or autonomy (that is A05's domain). Emission is idempotent: each
inbound message is durably accepted once (dedup by provider message id), so a
duplicate poll/webhook emits at most one event (I-07, I-13).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.connectors.binding import ConnectionBinding
from app.connectors.durable import DurableInboxPort, InboundEvent
from app.connectors.ports import ConnectorPort, payload_hash


@dataclass(frozen=True)
class MessageEvent:
    """A normalized inbound message. ``untrusted`` is always True (I-13).

    Carries provenance and content but no workflow decision. Consumers (A05) classify
    and route; A04 never sets ticket state here.
    """

    source: str
    account_ref: str
    external_id: str
    conversation_id: str
    from_email: str
    from_name: str
    subject: str
    body_text: str
    received_at: str
    store_id: UUID | None
    connection_id: UUID | None
    untrusted: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "conversation_id": self.conversation_id,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "subject": self.subject,
            "body_text": self.body_text,
            "received_at": self.received_at,
            "untrusted": self.untrusted,
            "store_id": str(self.store_id) if self.store_id else None,
            "connection_id": str(self.connection_id) if self.connection_id else None,
        }


class MessageEventSink(Protocol):
    """The A05-owned consumer contract. A04 only calls :meth:`emit`."""

    async def emit(self, event: MessageEvent) -> None: ...


class CollectingSink:
    """A test/in-memory sink that records emitted events."""

    def __init__(self) -> None:
        self.events: list[MessageEvent] = []

    async def emit(self, event: MessageEvent) -> None:
        self.events.append(event)


def normalize_inbox_message(raw: dict[str, Any], binding: ConnectionBinding) -> MessageEvent:
    return MessageEvent(
        source="inbox",
        account_ref=binding.account_ref,
        external_id=str(raw.get("external_id", "")),
        conversation_id=str(raw.get("conversation_id", "")),
        from_email=str(raw.get("from_email", "")),
        from_name=str(raw.get("from_name", "")),
        subject=str(raw.get("subject", "")),
        body_text=str(raw.get("body_text", "")),
        received_at=str(raw.get("received_at", "")),
        store_id=binding.store_id,
        connection_id=binding.connection_id,
    )


async def ingest_inbox_messages(
    port: ConnectorPort,
    inbox: DurableInboxPort,
    binding: ConnectionBinding,
    sink: MessageEventSink,
    *,
    limit: int = 25,
) -> list[MessageEvent]:
    """Durably accept inbox messages and emit a normalized event for each NEW one.

    Returns the events emitted this run (duplicates are skipped).
    """
    messages, _ = await port.fetch("messages", limit=limit)
    emitted: list[MessageEvent] = []
    for raw in messages:
        source_event_id = str(raw.get("external_id", ""))
        if not source_event_id:
            continue
        _, is_duplicate = await inbox.accept(
            InboundEvent(
                source="inbox",
                source_event_id=source_event_id,
                account_ref=binding.account_ref,
                topic="message",
                payload_hash=payload_hash(raw),
                verification="verified",
                occurred_at=_parse_received(raw.get("received_at")),
                brand_id=binding.brand_id,
                store_id=binding.store_id,
                connection_id=binding.connection_id,
            )
        )
        if is_duplicate:
            continue
        event = normalize_inbox_message(raw, binding)
        await sink.emit(event)
        emitted.append(event)
    return emitted


def _parse_received(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        from datetime import UTC

        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt
