"""Per-person task board (Build Spec §7.3).

Reshapes the boards/tasks concept into a lightweight per-person Kanban for the
brand's small team — lanes todo → doing → done, each card assigned to a member.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

TASK_LANES = ("todo", "doing", "done")


class TeamTask(QueryModel, table=True):
    __tablename__ = "team_tasks"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    title: str = Field(default="")
    assignee: str = Field(default="", index=True)
    status: str = Field(default="todo", index=True)  # todo | doing | done
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
