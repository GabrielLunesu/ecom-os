"""Insights: output of scheduled reflection jobs (Build Spec §4, §8.12).

Anomalies and alerts — delivery-window anomaly, refund-risk, ticket-spike — computed
from live data and surfaced on the Overview.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class Insight(QueryModel, table=True):
    __tablename__ = "insights"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    kind: str = Field(
        default="", index=True
    )  # delivery_window | refund_risk | ticket_spike | health
    severity: str = Field(default="info")  # info | warning | critical
    title: str = Field(default="")
    detail: str = Field(default="")
    data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
