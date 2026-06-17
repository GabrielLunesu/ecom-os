"""add secret_entries table

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-06-18 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("secret_entries"):
        op.create_table(
            "secret_entries",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("handle", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("ciphertext", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_secret_entries_brand_id"),
            "secret_entries",
            ["brand_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_secret_entries_handle"),
            "secret_entries",
            ["handle"],
            unique=True,
        )


def downgrade() -> None:
    if _has_table("secret_entries"):
        op.drop_index(op.f("ix_secret_entries_handle"), table_name="secret_entries")
        op.drop_index(op.f("ix_secret_entries_brand_id"), table_name="secret_entries")
        op.drop_table("secret_entries")
