"""Refund request model — the approval lane for the separate refund path.

Invariant 2: refunds never run autonomously from the CS agent. A refund is a
`RefundRequest` that a human approves; only then does the (separately scoped)
RefundExecutor act. Capability is defined by which tools exist — the CS agent
cannot create or execute one.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

REFUND_STATUSES = ("pending", "approved", "rejected", "executed", "failed")


class RefundRequest(QueryModel, table=True):
    __tablename__ = "refund_requests"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    ticket_id: UUID | None = Field(default=None, foreign_key="tickets.id", index=True)
    order_id: str = Field(default="")
    order_name: str = Field(default="")
    amount: float = Field(default=0.0)
    currency: str = Field(default="USD")
    reason: str = Field(default="")
    status: str = Field(default="pending", index=True)
    requested_by: str = Field(default="")
    approved_by: str = Field(default="")
    error: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = Field(default=None)
