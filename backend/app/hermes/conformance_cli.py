"""Conformance gate runner — reproducible evidence + release gate (Runtime §15.6).

Selects a transport from configuration, runs the conformance suite, and produces a
structured snapshot plus a pass/fail gate. The gate is RED until a real pinned Hermes is
configured and passes (DR-A03-01 / A03-R02) — a fixture or compat transport can never turn
it green, so "conformance evidence" cannot be faked. A09 mounts this as the release gate; the
moment a real Hermes endpoint (IR-A03-05) is provided, the same command yields real evidence.

Transport selection (by environment):
- ``HERMES_NATIVE_ENDPOINT`` set  → real Hermes native transport (is_real=True)
- ``HERMES_OPENCLAW_COMPAT_URL``  → OpenClaw compat transport (dev, is_real=False)
- otherwise                       → fixture transport (is_real=False)
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .bridge import HermesBridge
from .capabilities import FeatureReadiness
from .health import hermes_health_snapshot
from .native import HermesNativeConfig, HermesNativeTransport


@dataclass(frozen=True)
class SelectedTransport:
    bridge: HermesBridge
    label: str
    is_real: bool


def select_transport(env: Mapping[str, str]) -> SelectedTransport:
    """Pick the conformance transport from environment configuration."""
    endpoint = env.get("HERMES_NATIVE_ENDPOINT")
    if endpoint:
        config = HermesNativeConfig(
            endpoint=endpoint, token_handle=env.get("HERMES_NATIVE_TOKEN_HANDLE")
        )
        return SelectedTransport(HermesNativeTransport(config), "hermes-native", True)

    compat_url = env.get("HERMES_OPENCLAW_COMPAT_URL")
    if compat_url:
        # Imported lazily: the compat transport pulls the legacy OpenClaw stack + settings.
        from app.services.openclaw.gateway_rpc import GatewayConfig

        from .openclaw_compat import OpenClawCompatTransport

        bridge = OpenClawCompatTransport(GatewayConfig(url=compat_url))
        return SelectedTransport(bridge, "openclaw-compat", False)

    from .fake import FakeHermesTransport

    return SelectedTransport(FakeHermesTransport(), "fixture", False)


@dataclass(frozen=True)
class GateResult:
    ok: bool
    exit_code: int
    reason: str
    snapshot: dict[str, Any]


def evaluate_gate(snapshot: dict[str, Any]) -> GateResult:
    """Decide the release gate from a health snapshot (§15.6)."""
    if snapshot.get("conformance_blocked"):
        return GateResult(
            ok=False,
            exit_code=2,
            reason=(
                "BLOCKED: no real pinned Hermes — conformance evidence requires a real "
                "endpoint (A03-R02 / IR-A03-05)"
            ),
            snapshot=snapshot,
        )
    conformance = snapshot.get("conformance", {})
    if not conformance.get("passed", False):
        failures = conformance.get("failures", [])
        return GateResult(
            ok=False,
            exit_code=1,
            reason=f"conformance checks failed: {failures}",
            snapshot=snapshot,
        )
    not_ready = [
        name
        for name, readiness in snapshot.get("features", {}).items()
        if readiness == FeatureReadiness.not_ready.value
    ]
    if not_ready:
        return GateResult(
            ok=False,
            exit_code=1,
            reason=f"features not ready: {sorted(not_ready)}",
            snapshot=snapshot,
        )
    return GateResult(ok=True, exit_code=0, reason="all required features ready", snapshot=snapshot)


async def run_conformance_gate(env: Mapping[str, str]) -> GateResult:
    """Select a transport, run conformance, and evaluate the gate."""
    selected = select_transport(env)
    snapshot = await hermes_health_snapshot(
        selected.bridge,
        is_real=selected.is_real,
        transport_label=selected.label,
    )
    return evaluate_gate(snapshot)


async def _amain(env: Mapping[str, str]) -> int:
    result = await run_conformance_gate(env)
    print(json.dumps({"reason": result.reason, **result.snapshot}, indent=2))
    return result.exit_code


def main() -> None:  # pragma: no cover - thin CLI shell
    import os
    import sys

    import anyio

    sys.exit(anyio.run(_amain, os.environ))


if __name__ == "__main__":  # pragma: no cover
    main()
