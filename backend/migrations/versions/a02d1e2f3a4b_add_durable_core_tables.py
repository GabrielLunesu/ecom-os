"""add durable core event trace action tables

Revision ID: a02d1e2f3a4b
Revises: a0b1c2d3e4f5
Create Date: 2026-06-19 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a02d1e2f3a4b"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("traces"):
        op.create_table(
            "traces",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_type", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("brand_id", sa.Uuid(), nullable=True),
            sa.Column("store_id", sa.Uuid(), nullable=True),
            sa.Column("root_actor_type", sa.String(), nullable=False),
            sa.Column("root_actor_id", sa.String(), nullable=False),
            sa.Column("root_event_id", sa.Uuid(), nullable=True),
            sa.Column("root_job_id", sa.Uuid(), nullable=True),
            sa.Column("root_request_id", sa.String(), nullable=True),
            sa.Column("parent_trace_id", sa.Uuid(), nullable=True),
            sa.Column("primary_entity_type", sa.String(), nullable=True),
            sa.Column("primary_entity_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("coverage", sa.String(), nullable=False),
            sa.Column("retention_class", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("attributes", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_traces_entity", "traces", ["primary_entity_type", "primary_entity_id"]
        )
        op.create_index("ix_traces_scope_started", "traces", ["store_id", "started_at"])
        for column in (
            "trace_type",
            "brand_id",
            "store_id",
            "root_event_id",
            "root_job_id",
            "root_request_id",
            "parent_trace_id",
            "primary_entity_type",
            "primary_entity_id",
            "status",
            "coverage",
            "retention_class",
            "started_at",
            "ended_at",
        ):
            op.create_index(op.f(f"ix_traces_{column}"), "traces", [column])

    if not _has_table("runs"):
        op.create_table(
            "runs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=False),
            sa.Column("runtime", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("coverage", sa.String(), nullable=False),
            sa.Column("hermes_profile_id", sa.Uuid(), nullable=True),
            sa.Column("hermes_session_id", sa.String(), nullable=True),
            sa.Column("hermes_run_id", sa.String(), nullable=True),
            sa.Column("source_platform", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=True),
            sa.Column("prompt_hash", sa.String(), nullable=True),
            sa.Column("skill_hash", sa.String(), nullable=True),
            sa.Column("config_hash", sa.String(), nullable=True),
            sa.Column("end_reason", sa.String(), nullable=True),
            sa.Column("cost_minor_units", sa.Integer(), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("attributes", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in (
            "trace_id",
            "runtime",
            "status",
            "coverage",
            "hermes_profile_id",
            "hermes_session_id",
            "hermes_run_id",
            "source_platform",
            "prompt_hash",
            "skill_hash",
            "config_hash",
            "started_at",
            "ended_at",
        ):
            op.create_index(op.f(f"ix_runs_{column}"), "runs", [column])

    if not _has_table("spans"):
        op.create_table(
            "spans",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=False),
            sa.Column("run_id", sa.Uuid(), nullable=True),
            sa.Column("parent_span_id", sa.Uuid(), nullable=True),
            sa.Column("span_type", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("coverage", sa.String(), nullable=False),
            sa.Column("actor_type", sa.String(), nullable=True),
            sa.Column("actor_id", sa.String(), nullable=True),
            sa.Column("entity_type", sa.String(), nullable=True),
            sa.Column("entity_id", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("attributes", sa.JSON(), nullable=False),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
            sa.ForeignKeyConstraint(["trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_spans_trace_started", "spans", ["trace_id", "started_at"])
        for column in (
            "trace_id",
            "run_id",
            "parent_span_id",
            "span_type",
            "status",
            "coverage",
            "entity_type",
            "entity_id",
            "started_at",
            "ended_at",
            "error_code",
        ):
            op.create_index(op.f(f"ix_spans_{column}"), "spans", [column])

    if not _has_table("tool_invocations"):
        op.create_table(
            "tool_invocations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=False),
            sa.Column("run_id", sa.Uuid(), nullable=True),
            sa.Column("span_id", sa.Uuid(), nullable=True),
            sa.Column("tool_name", sa.String(), nullable=False),
            sa.Column("tool_version", sa.String(), nullable=False),
            sa.Column("schema_hash", sa.String(), nullable=False),
            sa.Column("transport", sa.String(), nullable=False),
            sa.Column("actor_type", sa.String(), nullable=False),
            sa.Column("actor_id", sa.String(), nullable=False),
            sa.Column("effective_identity_type", sa.String(), nullable=True),
            sa.Column("effective_identity_id", sa.String(), nullable=True),
            sa.Column("store_id", sa.Uuid(), nullable=True),
            sa.Column("connection_id", sa.Uuid(), nullable=True),
            sa.Column("hermes_profile_id", sa.Uuid(), nullable=True),
            sa.Column("hermes_session_id", sa.String(), nullable=True),
            sa.Column("hermes_run_id", sa.String(), nullable=True),
            sa.Column("hermes_tool_call_id", sa.String(), nullable=True),
            sa.Column("arguments_redacted", sa.JSON(), nullable=False),
            sa.Column("result_summary", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("coverage", sa.String(), nullable=False),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
            sa.ForeignKeyConstraint(["span_id"], ["spans.id"]),
            sa.ForeignKeyConstraint(["trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_tool_invocations_tool_started",
            "tool_invocations",
            ["tool_name", "started_at"],
        )
        for column in (
            "trace_id",
            "run_id",
            "span_id",
            "tool_name",
            "tool_version",
            "schema_hash",
            "transport",
            "store_id",
            "connection_id",
            "hermes_profile_id",
            "hermes_session_id",
            "hermes_run_id",
            "hermes_tool_call_id",
            "status",
            "coverage",
            "error_code",
            "started_at",
            "ended_at",
        ):
            op.create_index(
                op.f(f"ix_tool_invocations_{column}"), "tool_invocations", [column]
            )

    if not _has_table("durable_inbox_events"):
        op.create_table(
            "durable_inbox_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("source_scope", sa.String(), nullable=False),
            sa.Column("source_event_id", sa.String(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=True),
            sa.Column("store_id", sa.Uuid(), nullable=True),
            sa.Column("connection_id", sa.Uuid(), nullable=True),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("causation_event_id", sa.Uuid(), nullable=True),
            sa.Column("correlation_key", sa.String(), nullable=True),
            sa.Column("occurred_at", sa.DateTime(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=False),
            sa.Column("actor_type", sa.String(), nullable=True),
            sa.Column("actor_id", sa.String(), nullable=True),
            sa.Column("coverage", sa.String(), nullable=False),
            sa.Column("payload_hash", sa.String(), nullable=False),
            sa.Column("verification", sa.String(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("event_metadata", sa.JSON(), nullable=False),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("processing_error", sa.Text(), nullable=True),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source",
                "source_scope",
                "source_event_id",
                name="uq_durable_inbox_source_event",
            ),
        )
        op.create_index(
            "ix_durable_inbox_scope_state_received",
            "durable_inbox_events",
            ["source", "state", "received_at"],
        )
        for column in (
            "event_type",
            "source",
            "source_scope",
            "source_event_id",
            "brand_id",
            "store_id",
            "connection_id",
            "trace_id",
            "causation_event_id",
            "correlation_key",
            "occurred_at",
            "received_at",
            "coverage",
            "payload_hash",
            "verification",
            "state",
        ):
            op.create_index(
                op.f(f"ix_durable_inbox_events_{column}"),
                "durable_inbox_events",
                [column],
            )

    if not _has_table("durable_outbox_events"):
        op.create_table(
            "durable_outbox_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("topic", sa.String(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("deduplication_key", sa.String(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("next_run_at", sa.DateTime(), nullable=False),
            sa.Column("lease_owner", sa.String(), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "deduplication_key", name="uq_durable_outbox_deduplication_key"
            ),
        )
        op.create_index(
            "ix_durable_outbox_runnable",
            "durable_outbox_events",
            ["state", "next_run_at"],
        )
        op.create_index(
            "ix_durable_outbox_lease",
            "durable_outbox_events",
            ["lease_owner", "lease_expires_at"],
        )
        for column in (
            "topic",
            "deduplication_key",
            "trace_id",
            "state",
            "next_run_at",
            "lease_owner",
            "lease_expires_at",
            "created_at",
        ):
            op.create_index(
                op.f(f"ix_durable_outbox_events_{column}"),
                "durable_outbox_events",
                [column],
            )

    if not _has_table("durable_jobs"):
        op.create_table(
            "durable_jobs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("job_type", sa.String(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("deduplication_key", sa.String(), nullable=False),
            sa.Column("concurrency_key", sa.String(), nullable=True),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("next_run_at", sa.DateTime(), nullable=False),
            sa.Column("lease_owner", sa.String(), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
            sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_code", sa.String(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "job_type", "deduplication_key", name="uq_durable_jobs_dedupe"
            ),
        )
        op.create_index(
            "ix_durable_jobs_runnable", "durable_jobs", ["state", "next_run_at"]
        )
        op.create_index(
            "ix_durable_jobs_lease", "durable_jobs", ["lease_owner", "lease_expires_at"]
        )
        for column in (
            "job_type",
            "deduplication_key",
            "concurrency_key",
            "trace_id",
            "state",
            "next_run_at",
            "lease_owner",
            "lease_expires_at",
            "last_error_code",
            "created_at",
        ):
            op.create_index(op.f(f"ix_durable_jobs_{column}"), "durable_jobs", [column])

    if not _has_table("evidence"):
        op.create_table(
            "evidence",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("evidence_type", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("source_id", sa.String(), nullable=False),
            sa.Column("source_timestamp", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("trust_label", sa.String(), nullable=False),
            sa.Column("access_label", sa.String(), nullable=False),
            sa.Column("content_hash", sa.String(), nullable=False),
            sa.Column("excerpt", sa.Text(), nullable=True),
            sa.Column("reference", sa.String(), nullable=True),
            sa.Column("superseded_by_id", sa.Uuid(), nullable=True),
            sa.Column("evidence_metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_evidence_source_pair", "evidence", ["source", "source_id"])
        for column in (
            "evidence_type",
            "source",
            "source_id",
            "source_timestamp",
            "collected_at",
            "trust_label",
            "access_label",
            "content_hash",
            "superseded_by_id",
        ):
            op.create_index(op.f(f"ix_evidence_{column}"), "evidence", [column])

    if not _has_table("evidence_links"):
        op.create_table(
            "evidence_links",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("evidence_id", sa.Uuid(), nullable=False),
            sa.Column("target_type", sa.String(), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False),
            sa.Column("purpose", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_evidence_links_target", "evidence_links", ["target_type", "target_id"]
        )
        for column in (
            "evidence_id",
            "target_type",
            "target_id",
            "purpose",
            "created_at",
        ):
            op.create_index(
                op.f(f"ix_evidence_links_{column}"), "evidence_links", [column]
            )

    if not _has_table("audit_records"):
        op.create_table(
            "audit_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=True),
            sa.Column("actor_type", sa.String(), nullable=False),
            sa.Column("actor_id", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("target_type", sa.String(), nullable=True),
            sa.Column("target_id", sa.String(), nullable=True),
            sa.Column("before", sa.JSON(), nullable=True),
            sa.Column("after", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in (
            "trace_id",
            "actor_type",
            "actor_id",
            "action",
            "target_type",
            "target_id",
            "created_at",
        ):
            op.create_index(
                op.f(f"ix_audit_records_{column}"), "audit_records", [column]
            )

    if not _has_table("incidents"):
        op.create_table(
            "incidents",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("severity", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("owner_type", sa.String(), nullable=True),
            sa.Column("owner_id", sa.String(), nullable=True),
            sa.Column("detection_source", sa.String(), nullable=True),
            sa.Column("root_trace_id", sa.Uuid(), nullable=True),
            sa.Column("suspected_cause_category", sa.String(), nullable=True),
            sa.Column("root_cause_confidence", sa.String(), nullable=False),
            sa.Column("impact_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("incident_metadata", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["root_trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in (
            "severity",
            "status",
            "detection_source",
            "root_trace_id",
            "suspected_cause_category",
            "root_cause_confidence",
            "created_at",
        ):
            op.create_index(op.f(f"ix_incidents_{column}"), "incidents", [column])

    if not _has_table("actions"):
        op.create_table(
            "actions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trace_id", sa.Uuid(), nullable=False),
            sa.Column("tool_invocation_id", sa.Uuid(), nullable=True),
            sa.Column("action_type", sa.String(), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("connection_id", sa.Uuid(), nullable=False),
            sa.Column("target_type", sa.String(), nullable=False),
            sa.Column("target_id", sa.String(), nullable=False),
            sa.Column("normalized_arguments", sa.JSON(), nullable=False),
            sa.Column("action_digest", sa.String(), nullable=False),
            sa.Column("requested_actor_type", sa.String(), nullable=False),
            sa.Column("requested_actor_id", sa.String(), nullable=False),
            sa.Column("requested_run_id", sa.Uuid(), nullable=True),
            sa.Column("requested_session_id", sa.String(), nullable=True),
            sa.Column("effective_grant", sa.JSON(), nullable=False),
            sa.Column("autonomy_mode", sa.String(), nullable=False),
            sa.Column("policy_version", sa.String(), nullable=True),
            sa.Column("policy_result", sa.JSON(), nullable=True),
            sa.Column("approval_required", sa.Boolean(), nullable=False),
            sa.Column("approval_id", sa.Uuid(), nullable=True),
            sa.Column("intent_key", sa.String(), nullable=False),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("final_outcome_summary", sa.JSON(), nullable=True),
            sa.Column("reversibility", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tool_invocation_id"], ["tool_invocations.id"]),
            sa.ForeignKeyConstraint(["trace_id"], ["traces.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "store_id",
                "connection_id",
                "action_type",
                "intent_key",
                name="uq_actions_intent_scope",
            ),
        )
        op.create_index("ix_actions_target", "actions", ["target_type", "target_id"])
        op.create_index("ix_actions_state_created", "actions", ["state", "created_at"])
        for column in (
            "trace_id",
            "tool_invocation_id",
            "action_type",
            "store_id",
            "connection_id",
            "target_type",
            "target_id",
            "action_digest",
            "requested_actor_type",
            "requested_actor_id",
            "requested_run_id",
            "autonomy_mode",
            "policy_version",
            "approval_required",
            "approval_id",
            "intent_key",
            "state",
            "created_at",
        ):
            op.create_index(op.f(f"ix_actions_{column}"), "actions", [column])

    if not _has_table("action_state_history"):
        op.create_table(
            "action_state_history",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("action_id", sa.Uuid(), nullable=False),
            sa.Column("from_state", sa.String(), nullable=True),
            sa.Column("to_state", sa.String(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("actor_type", sa.String(), nullable=True),
            sa.Column("actor_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("transition_metadata", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["action_id"], ["actions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_action_state_history_action_created",
            "action_state_history",
            ["action_id", "created_at"],
        )
        for column in ("action_id", "from_state", "to_state", "created_at"):
            op.create_index(
                op.f(f"ix_action_state_history_{column}"),
                "action_state_history",
                [column],
            )

    if not _has_table("action_attempts"):
        op.create_table(
            "action_attempts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("action_id", sa.Uuid(), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("connector", sa.String(), nullable=False),
            sa.Column("connection_id", sa.Uuid(), nullable=False),
            sa.Column("provider_idempotency_key", sa.String(), nullable=False),
            sa.Column("request_fingerprint", sa.String(), nullable=False),
            sa.Column("safe_request_summary", sa.JSON(), nullable=False),
            sa.Column("provider_request_id", sa.String(), nullable=True),
            sa.Column("provider_operation_id", sa.String(), nullable=True),
            sa.Column("http_status_category", sa.String(), nullable=True),
            sa.Column("safe_response_summary", sa.JSON(), nullable=True),
            sa.Column("retry_classification", sa.String(), nullable=True),
            sa.Column("outcome_confidence", sa.String(), nullable=False),
            sa.Column("error_reference", sa.Text(), nullable=True),
            sa.Column("reconciliation_due_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["action_id"], ["actions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "action_id", "attempt_number", name="uq_action_attempts_action_number"
            ),
            sa.UniqueConstraint(
                "provider_idempotency_key",
                name="uq_action_attempts_provider_idempotency_key",
            ),
        )
        for column in (
            "action_id",
            "attempt_number",
            "connector",
            "connection_id",
            "provider_idempotency_key",
            "request_fingerprint",
            "provider_request_id",
            "provider_operation_id",
            "http_status_category",
            "retry_classification",
            "outcome_confidence",
            "reconciliation_due_at",
            "started_at",
            "ended_at",
        ):
            op.create_index(
                op.f(f"ix_action_attempts_{column}"), "action_attempts", [column]
            )


def downgrade() -> None:
    for table_name in (
        "action_attempts",
        "action_state_history",
        "actions",
        "incidents",
        "audit_records",
        "evidence_links",
        "evidence",
        "durable_jobs",
        "durable_outbox_events",
        "durable_inbox_events",
        "tool_invocations",
        "spans",
        "runs",
        "traces",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
