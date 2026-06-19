"""add A07 operator workspace tables

Revision ID: a07_20260619_operator_workspace
Revises: a0b1c2d3e4f5
Create Date: 2026-06-19 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a07_20260619_operator_workspace"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("operator_tasks"):
        op.create_table(
            "operator_tasks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("priority", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("assignee_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("assignee_id", sa.Uuid(), nullable=True),
            sa.Column("assignee_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("provenance", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_by_actor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_by_actor_id", sa.Uuid(), nullable=True),
            sa.Column("source_trace_id", sa.Uuid(), nullable=True),
            sa.Column("source_run_id", sa.Uuid(), nullable=True),
            sa.Column("source_evidence_ref", sqlmodel.sql.sqltypes.AutoString(length=256), nullable=True),
            sa.Column("access_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("daily_brief_include", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for col in (
            "brand_id",
            "title",
            "status",
            "priority",
            "due_at",
            "assignee_type",
            "assignee_id",
            "provenance",
            "created_by_actor_type",
            "created_by_actor_id",
            "source_trace_id",
            "source_run_id",
            "access_label",
            "daily_brief_include",
        ):
            op.create_index(op.f(f"ix_operator_tasks_{col}"), "operator_tasks", [col])

    if not _has_table("operator_task_entity_links"):
        op.create_table(
            "operator_task_entity_links",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("task_id", sa.Uuid(), nullable=False),
            sa.Column("entity_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("entity_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["operator_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for col in ("task_id", "entity_type", "entity_id", "trace_id"):
            op.create_index(
                op.f(f"ix_operator_task_entity_links_{col}"),
                "operator_task_entity_links",
                [col],
            )

    if not _has_table("operator_task_comments"):
        op.create_table(
            "operator_task_comments",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("task_id", sa.Uuid(), nullable=False),
            sa.Column("actor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("actor_id", sa.Uuid(), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["operator_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for col in ("task_id", "actor_type", "actor_id", "trace_id"):
            op.create_index(op.f(f"ix_operator_task_comments_{col}"), "operator_task_comments", [col])

    if not _has_table("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("logical_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("document_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("owner_actor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("owner_actor_id", sa.Uuid(), nullable=True),
            sa.Column("access_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("trust_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("current_version_id", sa.Uuid(), nullable=True),
            sa.Column("effective_date", sa.Date(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("ingestion_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("brand_id", "logical_path", name="uq_knowledge_documents_brand_path"),
        )
        for col in (
            "brand_id",
            "logical_path",
            "title",
            "document_type",
            "source",
            "owner_actor_type",
            "owner_actor_id",
            "access_label",
            "trust_label",
            "current_version_id",
            "effective_date",
            "expires_at",
            "ingestion_status",
        ):
            op.create_index(op.f(f"ix_knowledge_documents_{col}"), "knowledge_documents", [col])

    if not _has_table("knowledge_document_versions"):
        op.create_table(
            "knowledge_document_versions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("document_id", sa.Uuid(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("checksum", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("extracted_text", sa.Text(), nullable=False),
            sa.Column("extraction_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
            sa.Column("source_trace_id", sa.Uuid(), nullable=True),
            sa.Column("created_by_actor_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_by_actor_id", sa.Uuid(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id",
                "version_number",
                name="uq_knowledge_document_versions_doc_number",
            ),
        )
        for col in (
            "document_id",
            "version_number",
            "checksum",
            "extraction_status",
            "supersedes_version_id",
            "source_trace_id",
            "created_by_actor_type",
            "created_by_actor_id",
        ):
            op.create_index(
                op.f(f"ix_knowledge_document_versions_{col}"),
                "knowledge_document_versions",
                [col],
            )

    if not _has_table("knowledge_document_chunks"):
        op.create_table(
            "knowledge_document_chunks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("document_id", sa.Uuid(), nullable=False),
            sa.Column("version_id", sa.Uuid(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("access_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("trust_label", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
            sa.ForeignKeyConstraint(["version_id"], ["knowledge_document_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for col in ("document_id", "version_id", "chunk_index", "access_label", "trust_label"):
            op.create_index(
                op.f(f"ix_knowledge_document_chunks_{col}"),
                "knowledge_document_chunks",
                [col],
            )
        dialect = op.get_bind().dialect.name
        if dialect == "postgresql":
            op.execute(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_document_chunks_text_fts "
                "ON knowledge_document_chunks "
                "USING GIN (to_tsvector('english', text))"
            )

    if not _has_table("attention_snapshots"):
        op.create_table(
            "attention_snapshots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("source_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("window_start", sa.DateTime(), nullable=True),
            sa.Column("window_end", sa.DateTime(), nullable=True),
            sa.Column("input_count", sa.Integer(), nullable=False),
            sa.Column("item_count", sa.Integer(), nullable=False),
            sa.Column("inputs_json", sa.JSON(), nullable=True),
            sa.Column("items_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for col in ("brand_id", "status", "source_status", "window_start", "window_end", "input_count", "item_count"):
            op.create_index(op.f(f"ix_attention_snapshots_{col}"), "attention_snapshots", [col])


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if _has_table("attention_snapshots"):
        op.drop_table("attention_snapshots")
    if _has_table("knowledge_document_chunks"):
        if dialect == "postgresql":
            op.execute("DROP INDEX IF EXISTS ix_knowledge_document_chunks_text_fts")
        op.drop_table("knowledge_document_chunks")
    if _has_table("knowledge_document_versions"):
        op.drop_table("knowledge_document_versions")
    if _has_table("knowledge_documents"):
        op.drop_table("knowledge_documents")
    if _has_table("operator_task_comments"):
        op.drop_table("operator_task_comments")
    if _has_table("operator_task_entity_links"):
        op.drop_table("operator_task_entity_links")
    if _has_table("operator_tasks"):
        op.drop_table("operator_tasks")
