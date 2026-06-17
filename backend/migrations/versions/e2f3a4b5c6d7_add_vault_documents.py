"""add vault_documents table

Revision ID: e2f3a4b5c6d7
Revises: d1e2c3b4a5f6
Create Date: 2026-06-17 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "e2f3a4b5c6d7"
down_revision = "d1e2c3b4a5f6"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("vault_documents"):
        op.create_table(
            "vault_documents",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_vault_documents_brand_id"), "vault_documents", ["brand_id"], unique=False
        )
        op.create_index(
            op.f("ix_vault_documents_slug"), "vault_documents", ["slug"], unique=True
        )
        op.create_index(
            op.f("ix_vault_documents_title"), "vault_documents", ["title"], unique=False
        )


def downgrade() -> None:
    if _has_table("vault_documents"):
        op.drop_index(op.f("ix_vault_documents_title"), table_name="vault_documents")
        op.drop_index(op.f("ix_vault_documents_slug"), table_name="vault_documents")
        op.drop_index(op.f("ix_vault_documents_brand_id"), table_name="vault_documents")
        op.drop_table("vault_documents")
