"""Hermes system-health / capability snapshot (Runtime Spec §3.1, §15.6, Build Spec Slice 3).

Assembles a serializable view of the compatibility record, conformance result, and per-feature
readiness for the `/agents` capability panel and `/system` health surface. Real-Hermes
conformance is reported as BLOCKED until a real endpoint is probed (DR-A03-01) — it is never
presented as passing on a fixture.

This is a pure service within A03's ownership. The HTTP route that exposes it is registered by
the `/system` owner (A09) via an interface request; A03 supplies this function.
"""

from __future__ import annotations

from typing import Any

from .bridge import HermesBridge
from .channels import ChannelDeliveryService, DeliveryIntent
from .conformance import run_conformance_suite


async def hermes_health_snapshot(
    bridge: HermesBridge,
    *,
    is_real: bool = False,
    transport_label: str = "fixture",
    channel_service: ChannelDeliveryService | None = None,
    channel_intent: DeliveryIntent | None = None,
) -> dict[str, Any]:
    """Build the health/capability snapshot for System health and `/agents`."""
    health = await bridge.health()
    report = await run_conformance_suite(
        bridge,
        is_real=is_real,
        channel_service=channel_service,
        channel_intent=channel_intent,
    )
    return {
        "transport": transport_label,
        # Real Hermes conformance is only meaningful against a real endpoint (I-19).
        "real_hermes": is_real,
        "conformance_blocked": not is_real,
        "health": {
            "ok": health.ok,
            "version": health.version,
            "detail": health.detail,
        },
        "conformance": {
            "passed": report.passed,
            "protocol": [{"name": c.name, "passed": c.passed} for c in report.protocol],
            "channels": [{"name": c.name, "passed": c.passed} for c in report.channels],
            "tools": [{"name": c.name, "passed": c.passed} for c in report.tools],
            "failures": [c.name for c in report.failures()],
        },
        "features": {name: readiness.value for name, readiness in report.feature_readiness.items()},
    }
