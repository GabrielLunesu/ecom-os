"""Ticket ingestion + lifecycle (Build Spec §7.6, Invariants 3 & 4).

Ingestion pulls inbound mail from the support inbox (Composio) and creates tickets.
Every inbound message is stored `untrusted=True` — the CS pipeline treats it as
delimited data, never instructions (Invariant 4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.tickets import Ticket, TicketAudit, TicketEvidence, TicketMessage
from app.services.connectors.composio_inbox import (
    ComposioInboxConnector,
    discover_active_mail_account,
)
from app.services.connectors.secrets import ConnectionRef


# Local-parts that indicate automated/marketing senders, not support requests.
_AUTOMATED_MARKERS = (
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "notifications",
    "notification",
    "mailer-daemon",
    "postmaster",
    "bounce",
)


def _is_support_candidate(from_email: str) -> bool:
    """Skip obvious automated/marketing senders; real customer mail passes."""
    local = (from_email or "").split("@", 1)[0].lower()
    return bool(from_email) and not any(m in local for m in _AUTOMATED_MARKERS)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _seen(session: AsyncSession, external_id: str) -> bool:
    if not external_id:
        return False
    found = (
        await session.exec(
            select(TicketMessage).where(TicketMessage.external_id == external_id)
        )
    ).first()
    return found is not None


async def create_ticket_from_message(
    session: AsyncSession, brand: Brand, msg: dict[str, Any]
) -> Ticket:
    """Create a `new` ticket + its untrusted inbound message + an audit row."""
    received = _parse_dt(msg.get("received_at", ""))
    ticket = Ticket(
        brand_id=brand.id,
        subject=msg.get("subject", "(no subject)"),
        customer_email=msg.get("from_email", ""),
        customer_name=msg.get("from_name", ""),
        status="new",
        channel="email",
        external_ref=msg.get("conversation_id", ""),
        inbound_message_external_id=msg.get("external_id", ""),
        last_customer_msg_at=received,
    )
    session.add(ticket)
    await session.flush()

    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            direction="inbound",
            author=msg.get("from_email", ""),
            body=msg.get("body_text", ""),
            untrusted=True,  # Invariant 4
            external_id=msg.get("external_id", ""),
            created_at=received or utcnow(),
        )
    )
    session.add(
        TicketAudit(
            ticket_id=ticket.id,
            action="ingested",
            actor="system",
            detail=f"email from {msg.get('from_email', '')}",
        )
    )
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def list_tickets(session: AsyncSession) -> list[Ticket]:
    return list(
        (await session.exec(select(Ticket).order_by(Ticket.updated_at.desc()))).all()  # type: ignore[attr-defined]
    )


async def get_ticket(session: AsyncSession, ticket_id: UUID) -> Ticket | None:
    return (await session.exec(select(Ticket).where(Ticket.id == ticket_id))).first()


async def ticket_messages(session: AsyncSession, ticket_id: UUID) -> list[TicketMessage]:
    return list(
        (
            await session.exec(
                select(TicketMessage)
                .where(TicketMessage.ticket_id == ticket_id)
                .order_by(TicketMessage.created_at)  # type: ignore[arg-type]
            )
        ).all()
    )


async def ticket_evidence(session: AsyncSession, ticket_id: UUID) -> list[TicketEvidence]:
    return list(
        (
            await session.exec(
                select(TicketEvidence)
                .where(TicketEvidence.ticket_id == ticket_id)
                .order_by(TicketEvidence.created_at)  # type: ignore[arg-type]
            )
        ).all()
    )


async def _open_ticket_for_conversation(session: AsyncSession, conversation_id: str) -> Ticket | None:
    """Find a non-resolved ticket in the same email conversation, if any."""
    if not conversation_id:
        return None
    return (
        await session.exec(
            select(Ticket)
            .where(Ticket.external_ref == conversation_id, Ticket.status != "resolved")
            .order_by(Ticket.created_at.desc())  # type: ignore[attr-defined]
        )
    ).first()


async def append_reply(session: AsyncSession, ticket: Ticket, msg: dict[str, Any]) -> None:
    """Append a threaded customer reply to an existing ticket.

    Invariant 3 (sticky escalation): a reply to a `needs_rep` ticket appends + notifies
    and never re-triggers autonomous handling. A reply to an `awaiting_customer` ticket
    re-activates it so the flow resumes on the next loop pass.
    """
    received = _parse_dt(msg.get("received_at", ""))
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            direction="inbound",
            author=msg.get("from_email", ""),
            body=msg.get("body_text", ""),
            untrusted=True,  # Invariant 4
            external_id=msg.get("external_id", ""),
            created_at=received or utcnow(),
        )
    )
    ticket.last_customer_msg_at = received or utcnow()
    if ticket.status == "awaiting_customer":
        ticket.status = "auto_handling"  # resume the flow
        note = "customer replied; resuming flow"
    elif ticket.status == "needs_rep":
        note = "customer replied; rep notified (no auto-handling)"  # Invariant 3
    else:
        note = "customer replied"
    ticket.updated_at = utcnow()
    session.add(ticket)
    session.add(TicketAudit(ticket_id=ticket.id, action="customer_reply", actor="system", detail=note))
    await session.commit()


async def ingest_inbox(session: AsyncSession, brand: Brand, *, limit: int = 25) -> list[Ticket]:
    """Pull unread inbound mail; thread replies into open tickets, else create new."""
    account_id = await discover_active_mail_account()
    if not account_id:
        return []
    inbox = ComposioInboxConnector(ConnectionRef(provider="composio", external_id=account_id))
    messages = await inbox.list_messages(unread_only=True, limit=limit)

    created: list[Ticket] = []
    for msg in messages:
        if not _is_support_candidate(msg.get("from_email", "")):
            continue
        if await _seen(session, msg.get("external_id", "")):
            continue
        existing = await _open_ticket_for_conversation(session, msg.get("conversation_id", ""))
        if existing is not None:
            await append_reply(session, existing, msg)
            continue
        created.append(await create_ticket_from_message(session, brand, msg))
    return created
