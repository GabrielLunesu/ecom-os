"""add refund_requests table

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("refund_requests"):
        op.create_table(
            "refund_requests",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("ticket_id", sa.Uuid(), nullable=True),
            sa.Column("order_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("order_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("requested_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("approved_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_refund_requests_brand_id"), "refund_requests", ["brand_id"])
        op.create_index(op.f("ix_refund_requests_ticket_id"), "refund_requests", ["ticket_id"])
        op.create_index(op.f("ix_refund_requests_status"), "refund_requests", ["status"])


def downgrade() -> None:
    if _has_table("refund_requests"):
        op.drop_table("refund_requests")
