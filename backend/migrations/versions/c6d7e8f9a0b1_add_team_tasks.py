"""add team_tasks table

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("team_tasks"):
        op.create_table(
            "team_tasks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("assignee", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_team_tasks_brand_id"), "team_tasks", ["brand_id"])
        op.create_index(op.f("ix_team_tasks_assignee"), "team_tasks", ["assignee"])
        op.create_index(op.f("ix_team_tasks_status"), "team_tasks", ["status"])


def downgrade() -> None:
    if _has_table("team_tasks"):
        op.drop_table("team_tasks")
