"""add ticket tables

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("tickets"):
        op.create_table(
            "tickets",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=True),
            sa.Column("subject", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("customer_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("customer_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("channel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("external_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column(
                "inbound_message_external_id",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
            ),
            sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_customer_msg_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
            sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_tickets_brand_id"), "tickets", ["brand_id"])
        op.create_index(op.f("ix_tickets_store_id"), "tickets", ["store_id"])
        op.create_index(op.f("ix_tickets_status"), "tickets", ["status"])
        op.create_index(op.f("ix_tickets_customer_email"), "tickets", ["customer_email"])
        op.create_index(op.f("ix_tickets_external_ref"), "tickets", ["external_ref"])
        op.create_index(op.f("ix_tickets_assigned_user_id"), "tickets", ["assigned_user_id"])

    if not _has_table("ticket_messages"):
        op.create_table(
            "ticket_messages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("ticket_id", sa.Uuid(), nullable=False),
            sa.Column("direction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("author", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("untrusted", sa.Boolean(), nullable=False),
            sa.Column("external_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ticket_messages_ticket_id"), "ticket_messages", ["ticket_id"])

    if not _has_table("ticket_evidence"):
        op.create_table(
            "ticket_evidence",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("ticket_id", sa.Uuid(), nullable=False),
            sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("summary", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ticket_evidence_ticket_id"), "ticket_evidence", ["ticket_id"])

    if not _has_table("ticket_audit"):
        op.create_table(
            "ticket_audit",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("ticket_id", sa.Uuid(), nullable=False),
            sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("actor", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ticket_audit_ticket_id"), "ticket_audit", ["ticket_id"])


def downgrade() -> None:
    for tbl in ("ticket_audit", "ticket_evidence", "ticket_messages", "tickets"):
        if _has_table(tbl):
            op.drop_table(tbl)
