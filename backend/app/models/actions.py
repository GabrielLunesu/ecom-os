"""Durable action intent, attempt, and state-history models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, Text, UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class Action(QueryModel, table=True):
    """One intended external side effect under Ecom-OS control."""

    __tablename__ = "actions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "connection_id",
            "action_type",
            "intent_key",
            name="uq_actions_intent_scope",
        ),
        Index("ix_actions_target", "target_type", "target_id"),
        Index("ix_actions_state_created", "state", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trace_id: UUID = Field(foreign_key="traces.id", index=True)
    tool_invocation_id: UUID | None = Field(
        default=None,
        foreign_key="tool_invocations.id",
        index=True,
    )
    action_type: str = Field(index=True)
    schema_version: int = Field(default=1)
    store_id: UUID = Field(index=True)
    connection_id: UUID = Field(index=True)
    target_type: str = Field(index=True)
    target_id: str = Field(index=True)
    normalized_arguments: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    action_digest: str = Field(index=True)
    requested_actor_type: str = Field(index=True)
    requested_actor_id: str = Field(index=True)
    requested_run_id: UUID | None = Field(default=None, index=True)
    requested_session_id: str | None = Field(default=None, index=True)
    effective_grant: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    autonomy_mode: str = Field(index=True)
    policy_version: str | None = Field(default=None, index=True)
    policy_result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    approval_required: bool = Field(default=False, index=True)
    approval_id: UUID | None = Field(default=None, index=True)
    intent_key: str = Field(index=True)
    state: str = Field(default="proposed", index=True)
    final_outcome_summary: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    reversibility: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class ActionStateHistory(QueryModel, table=True):
    """Append-only action state transition record."""

    __tablename__ = "action_state_history"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_action_state_history_action_created", "action_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action_id: UUID = Field(foreign_key="actions.id", index=True)
    from_state: str | None = Field(default=None, index=True)
    to_state: str = Field(index=True)
    reason: str | None = Field(default=None, sa_column=Column(Text))
    actor_type: str | None = None
    actor_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    transition_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class ActionAttempt(QueryModel, table=True):
    """One connector/provider request while completing an action."""

    __tablename__ = "action_attempts"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "action_id",
            "attempt_number",
            name="uq_action_attempts_action_number",
        ),
        UniqueConstraint(
            "provider_idempotency_key",
            name="uq_action_attempts_provider_idempotency_key",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action_id: UUID = Field(foreign_key="actions.id", index=True)
    attempt_number: int = Field(index=True)
    connector: str = Field(index=True)
    connection_id: UUID = Field(index=True)
    provider_idempotency_key: str = Field(index=True)
    request_fingerprint: str = Field(index=True)
    safe_request_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    provider_request_id: str | None = Field(default=None, index=True)
    provider_operation_id: str | None = Field(default=None, index=True)
    http_status_category: str | None = Field(default=None, index=True)
    safe_response_summary: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    retry_classification: str | None = Field(default=None, index=True)
    outcome_confidence: str = Field(default="unknown", index=True)
    error_reference: str | None = Field(default=None, sa_column=Column(Text))
    reconciliation_due_at: datetime | None = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=utcnow, index=True)
    ended_at: datetime | None = Field(default=None, index=True)
