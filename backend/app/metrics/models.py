"""Persistent metric and daily brief records owned by A08."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, Column, Date, DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.metrics.briefs import DailyBriefSnapshot
from app.metrics.formulas import FreshnessStatus, MetricComponent, MetricSnapshot


class MetricSnapshotRecord(SQLModel, table=True):
    """Stored deterministic metric result with formula and coverage metadata."""

    __tablename__ = "metric_snapshots"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "metric_name",
            "formula_version",
            "window_start_at",
            "window_end_at",
            "currency",
            name="uq_metric_snapshots_window_formula",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    store_id: str = Field(index=True)
    metric_name: str = Field(index=True)
    display_name: str = Field(default="")
    formula_version: str = Field(index=True)
    schema_version: int = Field(default=1)
    reporting_date: date = Field(sa_column=Column(Date, nullable=False))
    reporting_timezone: str = Field(default="")
    window_start_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    window_end_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    currency: str = Field(index=True)
    value_minor: int = Field(sa_column=Column(BigInteger, nullable=False))
    coverage: str = Field(index=True)
    coverage_percent: int = Field(default=0)
    freshness: str = Field(index=True)
    attribution_window_days: int = Field(default=0)
    fx_basis: str = Field(default="")
    missing_component_kinds: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    trace_id: str | None = Field(default=None, index=True)
    calculation_status: str = Field(default="finalized", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    finalized_at: datetime = Field(default_factory=utcnow)

    @classmethod
    def from_domain(
        cls,
        *,
        brand_id: UUID,
        snapshot: MetricSnapshot,
        trace_id: str | None = None,
    ) -> "MetricSnapshotRecord":
        return cls(
            brand_id=brand_id,
            store_id=snapshot.store_id,
            metric_name=snapshot.metric_name,
            display_name=snapshot.display_name,
            formula_version=snapshot.formula_version,
            reporting_date=snapshot.window.local_date,
            reporting_timezone=snapshot.window.timezone,
            window_start_at=snapshot.window.start_utc,
            window_end_at=snapshot.window.end_utc,
            currency=snapshot.currency,
            value_minor=snapshot.value.minor,
            coverage=snapshot.coverage.value,
            coverage_percent=snapshot.coverage_percent,
            freshness=_freshness_for_snapshot(snapshot),
            attribution_window_days=snapshot.attribution_window_days,
            fx_basis=snapshot.fx_basis,
            missing_component_kinds=[kind.value for kind in snapshot.missing_component_kinds],
            warnings=list(snapshot.warnings),
            trace_id=trace_id,
        )


class MetricComponentRecord(SQLModel, table=True):
    """Stored metric component with contribution and evidence references."""

    __tablename__ = "metric_components"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    snapshot_id: UUID = Field(foreign_key="metric_snapshots.id", index=True)
    kind: str = Field(index=True)
    amount_minor: int = Field(sa_column=Column(BigInteger, nullable=False))
    contribution_minor: int = Field(sa_column=Column(BigInteger, nullable=False))
    currency: str = Field(index=True)
    source_ref: str = Field(index=True)
    source_timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    collected_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    coverage: str = Field(index=True)
    freshness: str = Field(index=True)
    evidence_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)

    @classmethod
    def from_domain(
        cls,
        *,
        snapshot_id: UUID,
        component: MetricComponent,
    ) -> "MetricComponentRecord":
        return cls(
            snapshot_id=snapshot_id,
            kind=component.kind.value,
            amount_minor=component.amount.minor,
            contribution_minor=component.contribution.minor,
            currency=component.amount.currency,
            source_ref=component.source_ref,
            source_timestamp=component.source_timestamp,
            collected_at=component.collected_at,
            coverage=component.coverage.value,
            freshness=component.freshness.value,
            evidence_refs=list(component.evidence_refs),
        )


class DailyBriefRecord(SQLModel, table=True):
    """Stored immutable deterministic daily brief input and fallback output."""

    __tablename__ = "daily_briefs"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "store_id",
            "reporting_date",
            "reporting_timezone",
            "revision",
            name="uq_daily_briefs_scope_revision",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    store_id: str = Field(index=True)
    schema_version: int = Field(default=1)
    revision: int = Field(default=1, index=True)
    status: str = Field(default="finalized", index=True)
    reporting_date: date = Field(sa_column=Column(Date, nullable=False))
    reporting_timezone: str = Field(default="")
    window_start_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    window_end_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    coverage: str = Field(index=True)
    coverage_percent: int = Field(default=0)
    metric_snapshot_ids: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    sections: list[dict[str, object]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    deterministic_fallback_text: str = Field(sa_column=Column(Text, nullable=False))
    final_text: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    final_body_hash: str = Field(index=True)
    narration_status: str = Field(default="not_requested", index=True)
    narration_error: str | None = Field(default=None)
    hermes_session_id: str | None = Field(default=None, index=True)
    hermes_run_id: str | None = Field(default=None, index=True)
    hermes_cron_ref: str | None = Field(default=None, index=True)
    trace_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    finalized_at: datetime = Field(default_factory=utcnow)
    delivered_at: datetime | None = Field(default=None)

    @classmethod
    def from_domain(
        cls,
        *,
        brand_id: UUID,
        snapshot: DailyBriefSnapshot,
    ) -> "DailyBriefRecord":
        return cls(
            brand_id=brand_id,
            store_id=snapshot.store_id,
            revision=snapshot.revision,
            reporting_date=snapshot.window.local_date,
            reporting_timezone=snapshot.window.timezone,
            window_start_at=snapshot.window.start_utc,
            window_end_at=snapshot.window.end_utc,
            coverage=snapshot.coverage.value,
            coverage_percent=snapshot.coverage_percent,
            metric_snapshot_ids=list(snapshot.metric_snapshot_ids),
            sections=[section.to_payload() for section in snapshot.sections],
            warnings=list(snapshot.warnings),
            deterministic_fallback_text=snapshot.deterministic_fallback_text,
            final_body_hash=snapshot.fallback_body_hash,
            trace_id=snapshot.trace_id,
            finalized_at=snapshot.generated_at,
        )


class DailyBriefDeliveryIntentRecord(SQLModel, table=True):
    """Idempotent intent for Hermes-native delivery of a stored daily brief."""

    __tablename__ = "daily_brief_delivery_intents"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_daily_brief_delivery_intents_idempotency_key",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brief_id: UUID = Field(foreign_key="daily_briefs.id", index=True)
    target_platform: str = Field(index=True)
    target_channel_ref: str = Field(index=True)
    idempotency_key: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    body_hash: str = Field(index=True)
    delivery_evidence: dict[str, object] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    attempt_count: int = Field(default=0)
    trace_id: str | None = Field(default=None, index=True)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    delivered_at: datetime | None = Field(default=None)


def _freshness_for_snapshot(snapshot: MetricSnapshot) -> str:
    freshness_values = {component.freshness for component in snapshot.components}
    if FreshnessStatus.UNAVAILABLE in freshness_values:
        return FreshnessStatus.UNAVAILABLE.value
    if FreshnessStatus.STALE in freshness_values:
        return FreshnessStatus.STALE.value
    return FreshnessStatus.CURRENT.value
