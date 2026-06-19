"""Tests for the conformance gate runner (Runtime Spec §15.6).

Proves: the gate is RED on a fixture (no real Hermes — conformance cannot be faked), transport
selection follows configuration, and the gate would go GREEN only against a real, passing
runtime.
"""

from __future__ import annotations

import pytest

from app.hermes.conformance_cli import (
    evaluate_gate,
    run_conformance_gate,
    select_transport,
)
from app.hermes.native import HermesNativeTransport


def test_select_fixture_when_unconfigured() -> None:
    selected = select_transport({})
    assert selected.label == "fixture"
    assert selected.is_real is False


def test_select_native_when_endpoint_set() -> None:
    selected = select_transport({"HERMES_NATIVE_ENDPOINT": "https://hermes.example"})
    assert selected.label == "hermes-native"
    assert selected.is_real is True
    assert isinstance(selected.bridge, HermesNativeTransport)


@pytest.mark.asyncio
async def test_gate_is_blocked_on_fixture() -> None:
    result = await run_conformance_gate({})
    assert result.ok is False
    assert result.exit_code == 2
    assert "BLOCKED" in result.reason


@pytest.mark.asyncio
async def test_gate_is_blocked_on_unconfigured_native() -> None:
    result = await run_conformance_gate({"HERMES_NATIVE_ENDPOINT": ""})  # empty → fixture
    assert result.ok is False  # still blocked


def test_evaluate_gate_green_on_real_ready_snapshot() -> None:
    # A hypothetical real, passing snapshot turns the gate green.
    snapshot = {
        "conformance_blocked": False,
        "conformance": {"passed": True, "failures": []},
        "features": {"main_chat": "ready", "background_runs": "ready", "channels": "degraded"},
    }
    result = evaluate_gate(snapshot)
    assert result.ok is True
    assert result.exit_code == 0


def test_evaluate_gate_red_when_feature_not_ready() -> None:
    snapshot = {
        "conformance_blocked": False,
        "conformance": {"passed": True, "failures": []},
        "features": {"main_chat": "not_ready"},
    }
    result = evaluate_gate(snapshot)
    assert result.ok is False
    assert "not ready" in result.reason


def test_evaluate_gate_red_when_conformance_failed() -> None:
    snapshot = {
        "conformance_blocked": False,
        "conformance": {"passed": False, "failures": ["interrupt"]},
        "features": {},
    }
    result = evaluate_gate(snapshot)
    assert result.ok is False
    assert "interrupt" in result.reason
