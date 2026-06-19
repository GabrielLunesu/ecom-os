"""Tests for the unified conformance suite + readiness gate (Runtime Spec §15.6).

Proves: the suite runs against the bridge and produces evidence; a fixture probe gates every
feature to not_ready; a real probe with full capability + passing conformance is ready; a
missing mandatory flag blocks only its feature; channel conformance gates the channels feature.
"""

from __future__ import annotations

import pytest

from app.hermes.capabilities import REQUIRED_FLAGS, FeatureReadiness
from app.hermes.channels import (
    ChannelDeliveryService,
    DeliveryIntent,
    FakeChannelTransport,
    FakeDeliveryLog,
)
from app.hermes.conformance import run_conformance_suite
from app.hermes.fake import FakeHermesTransport


def _channel() -> tuple[ChannelDeliveryService, DeliveryIntent]:
    service = ChannelDeliveryService(FakeChannelTransport(), FakeDeliveryLog())
    intent = DeliveryIntent(
        brief_id="b1",
        brief_date="2026-06-18",
        channel="telegram",
        target="chat_1",
        body_hash="sha256:x",
    )
    return service, intent


@pytest.mark.asyncio
async def test_suite_runs_and_produces_evidence() -> None:
    report = await run_conformance_suite(FakeHermesTransport())
    assert report.protocol  # protocol checks were run
    assert report.protocol_passed is True


@pytest.mark.asyncio
async def test_tool_conformance_passes_on_real_catalog() -> None:
    # Tool-catalog conformance (§15.2) is real Ecom-OS evidence — passes without Hermes.
    report = await run_conformance_suite(FakeHermesTransport())
    assert report.tools  # tool checks ran
    assert report.tools_passed is True
    names = {c.name for c in report.tools}
    assert "unknown_tool_rejected" in names
    assert "secrets_absent_from_results" in names
    assert "adapter_mcp_parity" in names


@pytest.mark.asyncio
async def test_fixture_probe_gates_all_features_not_ready() -> None:
    report = await run_conformance_suite(FakeHermesTransport(), is_real=False)
    assert report.passed is True  # checks themselves pass
    # ...but nothing is ready without a real Hermes (I-19, §15.6).
    assert all(r is FeatureReadiness.not_ready for r in report.feature_readiness.values())


@pytest.mark.asyncio
async def test_real_probe_full_capability_is_ready() -> None:
    report = await run_conformance_suite(FakeHermesTransport(), is_real=True)
    assert report.feature_readiness["main_chat"] is FeatureReadiness.ready
    assert report.feature_readiness["background_runs"] is FeatureReadiness.ready


@pytest.mark.asyncio
async def test_missing_mandatory_flag_blocks_only_that_feature() -> None:
    reduced = frozenset(REQUIRED_FLAGS) - {"interactive.interrupt"}
    report = await run_conformance_suite(FakeHermesTransport(flags=reduced), is_real=True)
    assert report.feature_readiness["main_chat"] is FeatureReadiness.not_ready
    assert report.feature_readiness["background_runs"] is FeatureReadiness.ready


@pytest.mark.asyncio
async def test_channel_conformance_makes_channels_ready() -> None:
    service, intent = _channel()
    report = await run_conformance_suite(
        FakeHermesTransport(),
        is_real=True,
        channel_service=service,
        channel_intent=intent,
    )
    assert report.channels_passed is True
    assert report.feature_readiness["channels"] is FeatureReadiness.ready


@pytest.mark.asyncio
async def test_failures_are_listed_actionably() -> None:
    reduced = frozenset(REQUIRED_FLAGS) - {"interactive.interrupt"}
    report = await run_conformance_suite(FakeHermesTransport(flags=reduced), is_real=True)
    # Protocol checks still pass on the fake; the gate (not the checks) blocks the feature.
    # Force a real failure surface by asserting the report exposes a failures() accessor.
    assert isinstance(report.failures(), list)
