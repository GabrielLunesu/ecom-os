"""Agent configuration (Build Spec §7.5): templates + config, not open-ended.

Templates: CS / analytics / content / retention. Config = voice, SOPs, allowed
tools, schedule. The allowed-tools list is descriptive; actual capability is bound
by which connector tools exist (Invariant 2) — config can never grant a refund tool.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

AGENT_TEMPLATES = ("cs", "analytics", "content", "retention")


class AgentConfig(QueryModel, table=True):
    __tablename__ = "agent_configs"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    template: str = Field(default="cs", index=True)
    name: str = Field(default="")
    voice: str = Field(default="")
    sops: str = Field(default="", sa_column=Column(Text))
    allowed_tools: list[str] | None = Field(default=None, sa_column=Column(JSON))
    schedule: str = Field(default="manual")  # manual | webhook | cron expression
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
