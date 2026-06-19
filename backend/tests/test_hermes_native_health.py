"""Tests for the native-transport boundary and the health snapshot.

Proves: the real-Hermes transport is an honest blocked stub (never pretends to work), and the
health snapshot reports `conformance_blocked` on fixtures while still exposing readiness.
"""

from __future__ import annotations

import pytest

from app.hermes.bridge import HermesBridge
from app.hermes.fake import FakeHermesTransport
from app.hermes.health import hermes_health_snapshot
from app.hermes.native import (
    HermesNativeConfig,
    HermesNativeNotConfigured,
    HermesNativeNotImplemented,
    HermesNativeTransport,
)
from app.hermes.types import CreateSession


def test_native_transport_satisfies_bridge_protocol() -> None:
    assert isinstance(HermesNativeTransport(), HermesBridge)


@pytest.mark.asyncio
async def test_unconfigured_native_health_is_blocked() -> None:
    transport = HermesNativeTransport()
    assert transport.configured is False
    health = await transport.health()
    assert health.ok is False
    assert "BLOCKED" in (health.detail or "")
    # No proven capabilities → nothing can be ready.
    caps = await transport.probe()
    assert caps.flags == frozenset()


@pytest.mark.asyncio
async def test_unconfigured_native_refuses_operations() -> None:
    transport = HermesNativeTransport()
    with pytest.raises(HermesNativeNotConfigured):
        await transport.create_session(CreateSession(profile_id="hp1"))


@pytest.mark.asyncio
async def test_configured_native_is_not_implemented_yet() -> None:
    transport = HermesNativeTransport(
        HermesNativeConfig(endpoint="https://hermes.example", token_handle="HERMES_TOKEN")
    )
    assert transport.configured is True
    with pytest.raises(HermesNativeNotImplemented):
        await transport.create_session(CreateSession(profile_id="hp1"))


@pytest.mark.asyncio
async def test_health_snapshot_fixture_is_conformance_blocked() -> None:
    snapshot = await hermes_health_snapshot(FakeHermesTransport())
    assert snapshot["conformance_blocked"] is True
    assert snapshot["real_hermes"] is False
    # readiness is exposed even while blocked; all not_ready on a fixture
    assert set(snapshot["features"].values()) == {"not_ready"}


@pytest.mark.asyncio
async def test_health_snapshot_real_exposes_ready_features() -> None:
    snapshot = await hermes_health_snapshot(
        FakeHermesTransport(), is_real=True, transport_label="hermes-native"
    )
    assert snapshot["conformance_blocked"] is False
    assert snapshot["features"]["main_chat"] == "ready"
    assert snapshot["conformance"]["passed"] is True


@pytest.mark.asyncio
async def test_health_snapshot_of_native_stub_reports_blocked() -> None:
    # The production transport, unconfigured, surfaces as fully blocked in System health.
    snapshot = await hermes_health_snapshot(
        HermesNativeTransport(), transport_label="hermes-native"
    )
    assert snapshot["health"]["ok"] is False
    assert snapshot["conformance_blocked"] is True
    assert set(snapshot["features"].values()) == {"not_ready"}
