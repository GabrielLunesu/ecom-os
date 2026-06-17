"""add agent_configs table

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("agent_configs"):
        op.create_table(
            "agent_configs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("template", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("voice", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("sops", sa.Text(), nullable=False),
            sa.Column("allowed_tools", sa.JSON(), nullable=True),
            sa.Column("schedule", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agent_configs_brand_id"), "agent_configs", ["brand_id"])
        op.create_index(op.f("ix_agent_configs_template"), "agent_configs", ["template"])


def downgrade() -> None:
    if _has_table("agent_configs"):
        op.drop_table("agent_configs")
