from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.metrics.formulas import (
    ComponentKind,
    FreshnessStatus,
    MetricComponentInput,
    Money,
    SourceCoverage,
    calculate_estimated_contribution_margin,
    reporting_window_for_local_day,
)
from app.metrics.models import MetricComponentRecord, MetricSnapshotRecord
from app.models.brand import Brand


def _snapshot_record() -> tuple[Brand, MetricSnapshotRecord, list[MetricComponentRecord]]:
    brand = Brand(name="A08 Test Brand")
    snapshot = calculate_estimated_contribution_margin(
        store_id="store_1",
        window=reporting_window_for_local_day(date(2026, 6, 17), "UTC"),
        currency="USD",
        components=[
            MetricComponentInput(
                kind=ComponentKind.NET_SALES,
                amount=Money(minor=10_000, currency="USD"),
                source_ref="orders",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.COMPLETE,
                freshness=FreshnessStatus.CURRENT,
                evidence_refs=["evidence:orders"],
            ),
            MetricComponentInput(
                kind=ComponentKind.COGS,
                amount=Money(minor=4_000, currency="USD"),
                source_ref="costs",
                source_timestamp=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),
                collected_at=datetime(2026, 6, 17, 12, 5, tzinfo=timezone.utc),
                coverage=SourceCoverage.PARTIAL,
                freshness=FreshnessStatus.STALE,
                evidence_refs=["evidence:costs"],
            ),
        ],
        attribution_window_days=7,
        fx_basis="provider_daily_close",
    )
    snapshot_record = MetricSnapshotRecord.from_domain(
        brand_id=brand.id,
        snapshot=snapshot,
        trace_id="trace_123",
    )
    component_records = [
        MetricComponentRecord.from_domain(snapshot_id=snapshot_record.id, component=component)
        for component in snapshot.components
    ]
    return brand, snapshot_record, component_records


def test_metric_snapshot_records_preserve_formula_evidence_and_coverage() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    brand, snapshot_record, component_records = _snapshot_record()

    with Session(engine) as session:
        session.add(brand)
        session.add(snapshot_record)
        session.add_all(component_records)
        session.commit()

        stored = session.exec(select(MetricSnapshotRecord)).one()
        components = session.exec(select(MetricComponentRecord)).all()

    assert stored.metric_name == "estimated_contribution_margin"
    assert stored.display_name == "Estimated contribution margin"
    assert stored.formula_version == "estimated_contribution_margin.v1"
    assert stored.value_minor == 6_000
    assert stored.currency == "USD"
    assert stored.coverage == SourceCoverage.PARTIAL.value
    assert stored.freshness == FreshnessStatus.STALE.value
    assert stored.coverage_percent < 100
    assert stored.trace_id == "trace_123"
    assert stored.missing_component_kinds
    assert any("Missing contribution components" in warning for warning in stored.warnings)
    assert {component.kind for component in components} == {
        ComponentKind.NET_SALES.value,
        ComponentKind.COGS.value,
    }
    assert {component.evidence_refs[0] for component in components} == {
        "evidence:orders",
        "evidence:costs",
    }


def test_metric_snapshot_window_formula_uniqueness_enforces_idempotency() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    brand, snapshot_record, _component_records = _snapshot_record()
    duplicate = MetricSnapshotRecord(
        brand_id=snapshot_record.brand_id,
        store_id=snapshot_record.store_id,
        metric_name=snapshot_record.metric_name,
        display_name=snapshot_record.display_name,
        formula_version=snapshot_record.formula_version,
        reporting_date=snapshot_record.reporting_date,
        reporting_timezone=snapshot_record.reporting_timezone,
        window_start_at=snapshot_record.window_start_at,
        window_end_at=snapshot_record.window_end_at,
        currency=snapshot_record.currency,
        value_minor=snapshot_record.value_minor,
        coverage=snapshot_record.coverage,
        coverage_percent=snapshot_record.coverage_percent,
        freshness=snapshot_record.freshness,
        attribution_window_days=snapshot_record.attribution_window_days,
        fx_basis=snapshot_record.fx_basis,
        missing_component_kinds=list(snapshot_record.missing_component_kinds),
        warnings=list(snapshot_record.warnings),
        trace_id=snapshot_record.trace_id,
    )

    with Session(engine) as session:
        session.add(brand)
        session.add(snapshot_record)
        session.commit()
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
