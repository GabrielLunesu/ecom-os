"""add brand and stores tables

Revision ID: d1e2c3b4a5f6
Revises: a9b1c2d3e4f7
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2c3b4a5f6"
down_revision = "a9b1c2d3e4f7"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("brands"):
        op.create_table(
            "brands",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_brands_name"), "brands", ["name"], unique=False)

    if not _has_table("stores"):
        op.create_table(
            "stores",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("domain", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("external_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_stores_brand_id"), "stores", ["brand_id"], unique=False)
        op.create_index(op.f("ix_stores_name"), "stores", ["name"], unique=False)
        op.create_index(op.f("ix_stores_domain"), "stores", ["domain"], unique=True)
        op.create_index(op.f("ix_stores_status"), "stores", ["status"], unique=False)


def downgrade() -> None:
    if _has_table("stores"):
        op.drop_index(op.f("ix_stores_status"), table_name="stores")
        op.drop_index(op.f("ix_stores_domain"), table_name="stores")
        op.drop_index(op.f("ix_stores_name"), table_name="stores")
        op.drop_index(op.f("ix_stores_brand_id"), table_name="stores")
        op.drop_table("stores")
    if _has_table("brands"):
        op.drop_index(op.f("ix_brands_name"), table_name="brands")
        op.drop_table("brands")
