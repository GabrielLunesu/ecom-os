"""add flows table + ticket flow state

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_table("flows"):
        op.create_table(
            "flows",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("intent", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("triggers", sa.JSON(), nullable=True),
            sa.Column("escalate_keywords", sa.JSON(), nullable=True),
            sa.Column("steps", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_flows_brand_id"), "flows", ["brand_id"])
        op.create_index(op.f("ix_flows_intent"), "flows", ["intent"])

    if not _has_column("tickets", "flow_id"):
        op.add_column("tickets", sa.Column("flow_id", sa.Uuid(), nullable=True))
        op.add_column("tickets", sa.Column("flow_step", sa.Integer(), nullable=False, server_default="0"))
        op.add_column("tickets", sa.Column("flow_data", sa.JSON(), nullable=True))
        op.create_index(op.f("ix_tickets_flow_id"), "tickets", ["flow_id"])
        op.create_foreign_key("fk_tickets_flow_id", "tickets", "flows", ["flow_id"], ["id"])


def downgrade() -> None:
    if _has_column("tickets", "flow_id"):
        op.drop_constraint("fk_tickets_flow_id", "tickets", type_="foreignkey")
        op.drop_index(op.f("ix_tickets_flow_id"), table_name="tickets")
        op.drop_column("tickets", "flow_data")
        op.drop_column("tickets", "flow_step")
        op.drop_column("tickets", "flow_id")
    if _has_table("flows"):
        op.drop_table("flows")
