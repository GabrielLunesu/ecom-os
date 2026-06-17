"""Flow model — a merchant-configurable CS SOP (Build Spec §7.5 / product direction).

A flow is a declarative sequence of deterministic steps for one ticket intent. The
merchant edits flows in the dashboard (no code); classification routes a ticket to a
flow; the engine runs the steps. Only the customer-facing wording is templated.

Invariants are structural, not configurable: a flow can offer discounts (capped) but
can NEVER auto-refund — the `request_refund_approval` step only files an approval in
the gated lane (Invariant 2). Escalation is sticky (Invariant 3); customer text is
untrusted data (Invariant 4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class Flow(QueryModel, table=True):
    __tablename__ = "flows"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    name: str = Field(default="")
    intent: str = Field(default="", index=True)  # e.g. "wismo" | "refund"
    # Keywords that route a ticket to this flow (lowercased substring match).
    triggers: list[str] | None = Field(default=None, sa_column=Column(JSON))
    # Words that force an immediate human escalation at any step.
    escalate_keywords: list[str] | None = Field(default=None, sa_column=Column(JSON))
    # Ordered list of step dicts: {"type": ..., ...}. See services/flow_engine.py.
    steps: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    enabled: bool = Field(default=True)
    position: int = Field(default=0)  # lower runs first when multiple match
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
