"""add store profile fields

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-06-18 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None

_COLS = ["public_url", "support_email", "support_name", "tracking_url"]


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    for col in _COLS:
        if not _has_column("stores", col):
            op.add_column(
                "stores",
                sa.Column(col, sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
            )
    if not _has_column("stores", "facts"):
        op.add_column("stores", sa.Column("facts", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    for col in ["facts", *_COLS]:
        if _has_column("stores", col):
            op.drop_column("stores", col)
