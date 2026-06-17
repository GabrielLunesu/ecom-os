"""CS ticket models: tickets + messages + evidence + audit (Build Spec §4).

Invariant 3 (sticky escalation): once `status == needs_rep`, the CS loop never
re-triggers autonomous handling — inbound replies only append + notify.
Invariant 4 (untrusted input): every inbound message is stored with `untrusted=True`;
the CS pipeline treats that text as delimited data, never as instructions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

# Lane order for the CS Kanban (Build Spec §7.6).
TICKET_STATUSES = (
    "new",
    "auto_handling",
    "awaiting_customer",
    "needs_rep",
    "resolved",
)


class Ticket(QueryModel, table=True):
    __tablename__ = "tickets"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    store_id: UUID | None = Field(default=None, foreign_key="stores.id", index=True)
    subject: str = Field(default="(no subject)")
    customer_email: str = Field(default="", index=True)
    customer_name: str = Field(default="")
    status: str = Field(default="new", index=True)
    channel: str = Field(default="email")
    # The email conversation id + the inbound message id to reply to (refs, not secrets).
    external_ref: str = Field(default="", index=True)
    inbound_message_external_id: str = Field(default="")
    assigned_user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_customer_msg_at: datetime | None = Field(default=None)


class TicketMessage(QueryModel, table=True):
    __tablename__ = "ticket_messages"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="tickets.id", index=True)
    direction: str = Field(default="inbound")  # inbound | outbound
    author: str = Field(default="")  # email address or agent identifier
    body: str = Field(default="", sa_column=Column(Text))
    # Invariant 4: inbound customer text is untrusted data, never instructions.
    untrusted: bool = Field(default=True)
    external_id: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)


class TicketEvidence(QueryModel, table=True):
    __tablename__ = "ticket_evidence"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="tickets.id", index=True)
    kind: str = Field(default="")  # order_lookup | policy_cite | tracking
    summary: str = Field(default="")
    data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class TicketAudit(QueryModel, table=True):
    __tablename__ = "ticket_audit"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticket_id: UUID = Field(foreign_key="tickets.id", index=True)
    action: str = Field(default="")
    actor: str = Field(default="system")
    detail: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
