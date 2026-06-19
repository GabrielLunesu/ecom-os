"""Durable event inbox, outbox, and leased job models for the v2 core."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, Text, UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class DurableInboxEvent(QueryModel, table=True):
    """Immutable accepted inbound event envelope."""

    __tablename__ = "durable_inbox_events"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_scope",
            "source_event_id",
            name="uq_durable_inbox_source_event",
        ),
        Index("ix_durable_inbox_scope_state_received", "source", "state", "received_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_type: str = Field(index=True)
    schema_version: int = Field(default=1)
    source: str = Field(index=True)
    source_scope: str = Field(default="", index=True)
    source_event_id: str = Field(index=True)
    brand_id: UUID | None = Field(default=None, index=True)
    store_id: UUID | None = Field(default=None, index=True)
    connection_id: UUID | None = Field(default=None, index=True)
    trace_id: UUID | None = Field(default=None, index=True)
    causation_event_id: UUID | None = Field(default=None, index=True)
    correlation_key: str | None = Field(default=None, index=True)
    occurred_at: datetime | None = Field(default=None, index=True)
    received_at: datetime = Field(default_factory=utcnow, index=True)
    actor_type: str | None = None
    actor_id: str | None = None
    coverage: str = Field(default="imported", index=True)
    payload_hash: str = Field(index=True)
    verification: str = Field(default="valid", index=True)
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    event_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    state: str = Field(default="accepted", index=True)
    processing_error: str | None = Field(default=None, sa_column=Column(Text))
    processed_at: datetime | None = None


class DurableOutboxEvent(QueryModel, table=True):
    """Transactional outbox row for effects leaving a DB transaction."""

    __tablename__ = "durable_outbox_events"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("deduplication_key", name="uq_durable_outbox_deduplication_key"),
        Index("ix_durable_outbox_runnable", "state", "next_run_at"),
        Index("ix_durable_outbox_lease", "lease_owner", "lease_expires_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    topic: str = Field(index=True)
    schema_version: int = Field(default=1)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    deduplication_key: str = Field(index=True)
    trace_id: UUID | None = Field(default=None, index=True)
    state: str = Field(default="pending", index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=5)
    next_run_at: datetime = Field(default_factory=utcnow, index=True)
    lease_owner: str | None = Field(default=None, index=True)
    lease_expires_at: datetime | None = Field(default=None, index=True)
    last_error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    delivered_at: datetime | None = None


class DurableJob(QueryModel, table=True):
    """Postgres-backed job with leases, bounded retry, and concurrency keys."""

    __tablename__ = "durable_jobs"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("job_type", "deduplication_key", name="uq_durable_jobs_dedupe"),
        Index("ix_durable_jobs_runnable", "state", "next_run_at"),
        Index("ix_durable_jobs_lease", "lease_owner", "lease_expires_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_type: str = Field(index=True)
    schema_version: int = Field(default=1)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    deduplication_key: str = Field(default="", index=True)
    concurrency_key: str | None = Field(default=None, index=True)
    trace_id: UUID | None = Field(default=None, index=True)
    state: str = Field(default="queued", index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    next_run_at: datetime = Field(default_factory=utcnow, index=True)
    lease_owner: str | None = Field(default=None, index=True)
    lease_expires_at: datetime | None = Field(default=None, index=True)
    heartbeat_at: datetime | None = None
    last_error_code: str | None = Field(default=None, index=True)
    last_error: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
