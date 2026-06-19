"""add A08 metric snapshot, component, and daily brief tables

Revision ID: a08_001_metric_snapshots
Revises: a0b1c2d3e4f5
Create Date: 2026-06-19 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a08_001_metric_snapshots"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("metric_snapshots"):
        op.create_table(
            "metric_snapshots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("metric_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("formula_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("reporting_date", sa.Date(), nullable=False),
            sa.Column("reporting_timezone", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("value_minor", sa.BigInteger(), nullable=False),
            sa.Column("coverage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("coverage_percent", sa.Integer(), nullable=False),
            sa.Column("freshness", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("attribution_window_days", sa.Integer(), nullable=False),
            sa.Column("fx_basis", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("missing_component_kinds", sa.JSON(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("trace_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("calculation_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finalized_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "store_id",
                "metric_name",
                "formula_version",
                "window_start_at",
                "window_end_at",
                "currency",
                name="uq_metric_snapshots_window_formula",
            ),
        )
        op.create_index(op.f("ix_metric_snapshots_brand_id"), "metric_snapshots", ["brand_id"])
        op.create_index(op.f("ix_metric_snapshots_store_id"), "metric_snapshots", ["store_id"])
        op.create_index(
            op.f("ix_metric_snapshots_metric_name"),
            "metric_snapshots",
            ["metric_name"],
        )
        op.create_index(
            op.f("ix_metric_snapshots_formula_version"),
            "metric_snapshots",
            ["formula_version"],
        )
        op.create_index(op.f("ix_metric_snapshots_currency"), "metric_snapshots", ["currency"])
        op.create_index(op.f("ix_metric_snapshots_coverage"), "metric_snapshots", ["coverage"])
        op.create_index(op.f("ix_metric_snapshots_freshness"), "metric_snapshots", ["freshness"])
        op.create_index(op.f("ix_metric_snapshots_trace_id"), "metric_snapshots", ["trace_id"])
        op.create_index(
            op.f("ix_metric_snapshots_calculation_status"),
            "metric_snapshots",
            ["calculation_status"],
        )

    if not _has_table("metric_components"):
        op.create_table(
            "metric_components",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("snapshot_id", sa.Uuid(), nullable=False),
            sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("amount_minor", sa.BigInteger(), nullable=False),
            sa.Column("contribution_minor", sa.BigInteger(), nullable=False),
            sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("source_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("coverage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("freshness", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("evidence_refs", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["metric_snapshots.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_metric_components_snapshot_id"),
            "metric_components",
            ["snapshot_id"],
        )
        op.create_index(op.f("ix_metric_components_kind"), "metric_components", ["kind"])
        op.create_index(op.f("ix_metric_components_currency"), "metric_components", ["currency"])
        op.create_index(op.f("ix_metric_components_source_ref"), "metric_components", ["source_ref"])
        op.create_index(op.f("ix_metric_components_coverage"), "metric_components", ["coverage"])
        op.create_index(op.f("ix_metric_components_freshness"), "metric_components", ["freshness"])

    if not _has_table("daily_briefs"):
        op.create_table(
            "daily_briefs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("reporting_date", sa.Date(), nullable=False),
            sa.Column("reporting_timezone", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("coverage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("coverage_percent", sa.Integer(), nullable=False),
            sa.Column("metric_snapshot_ids", sa.JSON(), nullable=False),
            sa.Column("sections", sa.JSON(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("deterministic_fallback_text", sa.Text(), nullable=False),
            sa.Column("final_text", sa.Text(), nullable=True),
            sa.Column("final_body_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("narration_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("narration_error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("hermes_session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("hermes_run_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("hermes_cron_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("trace_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finalized_at", sa.DateTime(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "brand_id",
                "store_id",
                "reporting_date",
                "reporting_timezone",
                "revision",
                name="uq_daily_briefs_scope_revision",
            ),
        )
        op.create_index(op.f("ix_daily_briefs_brand_id"), "daily_briefs", ["brand_id"])
        op.create_index(op.f("ix_daily_briefs_store_id"), "daily_briefs", ["store_id"])
        op.create_index(op.f("ix_daily_briefs_revision"), "daily_briefs", ["revision"])
        op.create_index(op.f("ix_daily_briefs_status"), "daily_briefs", ["status"])
        op.create_index(op.f("ix_daily_briefs_coverage"), "daily_briefs", ["coverage"])
        op.create_index(
            op.f("ix_daily_briefs_final_body_hash"),
            "daily_briefs",
            ["final_body_hash"],
        )
        op.create_index(
            op.f("ix_daily_briefs_narration_status"),
            "daily_briefs",
            ["narration_status"],
        )
        op.create_index(
            op.f("ix_daily_briefs_hermes_session_id"),
            "daily_briefs",
            ["hermes_session_id"],
        )
        op.create_index(
            op.f("ix_daily_briefs_hermes_run_id"),
            "daily_briefs",
            ["hermes_run_id"],
        )
        op.create_index(
            op.f("ix_daily_briefs_hermes_cron_ref"),
            "daily_briefs",
            ["hermes_cron_ref"],
        )
        op.create_index(op.f("ix_daily_briefs_trace_id"), "daily_briefs", ["trace_id"])

    if not _has_table("daily_brief_delivery_intents"):
        op.create_table(
            "daily_brief_delivery_intents",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brief_id", sa.Uuid(), nullable=False),
            sa.Column("target_platform", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("target_channel_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("idempotency_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("body_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("delivery_evidence", sa.JSON(), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False),
            sa.Column("trace_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["brief_id"], ["daily_briefs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "idempotency_key",
                name="uq_daily_brief_delivery_intents_idempotency_key",
            ),
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_brief_id"),
            "daily_brief_delivery_intents",
            ["brief_id"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_target_platform"),
            "daily_brief_delivery_intents",
            ["target_platform"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_target_channel_ref"),
            "daily_brief_delivery_intents",
            ["target_channel_ref"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_idempotency_key"),
            "daily_brief_delivery_intents",
            ["idempotency_key"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_status"),
            "daily_brief_delivery_intents",
            ["status"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_body_hash"),
            "daily_brief_delivery_intents",
            ["body_hash"],
        )
        op.create_index(
            op.f("ix_daily_brief_delivery_intents_trace_id"),
            "daily_brief_delivery_intents",
            ["trace_id"],
        )


def downgrade() -> None:
    if _has_table("daily_brief_delivery_intents"):
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_trace_id"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_body_hash"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_status"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_idempotency_key"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_target_channel_ref"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_target_platform"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_index(
            op.f("ix_daily_brief_delivery_intents_brief_id"),
            table_name="daily_brief_delivery_intents",
        )
        op.drop_table("daily_brief_delivery_intents")

    if _has_table("daily_briefs"):
        op.drop_index(op.f("ix_daily_briefs_trace_id"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_hermes_cron_ref"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_hermes_run_id"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_hermes_session_id"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_narration_status"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_final_body_hash"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_coverage"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_status"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_revision"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_store_id"), table_name="daily_briefs")
        op.drop_index(op.f("ix_daily_briefs_brand_id"), table_name="daily_briefs")
        op.drop_table("daily_briefs")

    if _has_table("metric_components"):
        op.drop_index(op.f("ix_metric_components_freshness"), table_name="metric_components")
        op.drop_index(op.f("ix_metric_components_coverage"), table_name="metric_components")
        op.drop_index(op.f("ix_metric_components_source_ref"), table_name="metric_components")
        op.drop_index(op.f("ix_metric_components_currency"), table_name="metric_components")
        op.drop_index(op.f("ix_metric_components_kind"), table_name="metric_components")
        op.drop_index(op.f("ix_metric_components_snapshot_id"), table_name="metric_components")
        op.drop_table("metric_components")

    if _has_table("metric_snapshots"):
        op.drop_index(
            op.f("ix_metric_snapshots_calculation_status"),
            table_name="metric_snapshots",
        )
        op.drop_index(op.f("ix_metric_snapshots_trace_id"), table_name="metric_snapshots")
        op.drop_index(op.f("ix_metric_snapshots_freshness"), table_name="metric_snapshots")
        op.drop_index(op.f("ix_metric_snapshots_coverage"), table_name="metric_snapshots")
        op.drop_index(op.f("ix_metric_snapshots_currency"), table_name="metric_snapshots")
        op.drop_index(
            op.f("ix_metric_snapshots_formula_version"),
            table_name="metric_snapshots",
        )
        op.drop_index(op.f("ix_metric_snapshots_metric_name"), table_name="metric_snapshots")
        op.drop_index(op.f("ix_metric_snapshots_store_id"), table_name="metric_snapshots")
        op.drop_index(op.f("ix_metric_snapshots_brand_id"), table_name="metric_snapshots")
        op.drop_table("metric_snapshots")
