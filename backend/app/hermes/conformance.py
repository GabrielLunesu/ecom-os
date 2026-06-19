"""Unified conformance suite + readiness gate (Runtime Spec §15).

Runs the protocol conformance (and optionally a channel conformance) against any
``HermesBridge`` and combines the results with capability negotiation into a per-feature
readiness gate (§15.6): a required conformance failure, a missing mandatory flag, or a
fixture probe all set the dependent feature to ``not_ready``. Failures are actionable and
surfaced in ``/agents`` / System health.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .bridge import HermesBridge
from .capabilities import (
    FEATURE_REQUIREMENTS,
    FeatureReadiness,
    evaluate_feature,
)
from .channels import ChannelDeliveryService, DeliveryIntent, DeliveryStatus
from .probe import run_conformance

# Features whose readiness depends on the interactive/background protocol conformance.
_PROTOCOL_FEATURES = frozenset({"main_chat", "background_runs", "external_tools"})


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class ConformanceReport:
    is_real: bool
    protocol: tuple[CheckResult, ...]
    channels: tuple[CheckResult, ...]
    feature_readiness: dict[str, FeatureReadiness] = field(default_factory=dict)

    @property
    def protocol_passed(self) -> bool:
        return all(c.passed for c in self.protocol)

    @property
    def channels_passed(self) -> bool:
        return all(c.passed for c in self.channels)

    @property
    def passed(self) -> bool:
        return self.protocol_passed and self.channels_passed

    def failures(self) -> list[CheckResult]:
        return [c for c in (*self.protocol, *self.channels) if not c.passed]


async def run_conformance_suite(
    bridge: HermesBridge,
    *,
    is_real: bool = False,
    channel_service: ChannelDeliveryService | None = None,
    channel_intent: DeliveryIntent | None = None,
) -> ConformanceReport:
    capabilities = await bridge.probe()

    protocol_result = await run_conformance(bridge)
    protocol_checks = tuple(
        CheckResult(name=name, passed=ok) for name, ok in protocol_result.checks
    )

    channel_checks: tuple[CheckResult, ...] = ()
    if channel_service is not None and channel_intent is not None:
        first = await channel_service.deliver(channel_intent)
        second = await channel_service.deliver(channel_intent)
        channel_checks = (
            CheckResult("channel_delivers", first.status is DeliveryStatus.delivered),
            CheckResult(
                "channel_idempotent", second.status is DeliveryStatus.duplicate
            ),
        )

    protocol_ok = all(c.passed for c in protocol_checks)
    channels_ok = all(c.passed for c in channel_checks)

    readiness: dict[str, FeatureReadiness] = {}
    for feature in FEATURE_REQUIREMENTS:
        evaluation = evaluate_feature(capabilities, feature)
        result = evaluation.readiness
        if not is_real:
            # A fixture probe never proves the production contract (I-19, §15.6).
            result = FeatureReadiness.not_ready
        elif feature in _PROTOCOL_FEATURES and not protocol_ok:
            result = FeatureReadiness.not_ready
        elif feature == "channels" and channel_checks and not channels_ok:
            result = FeatureReadiness.not_ready
        readiness[feature] = result

    return ConformanceReport(
        is_real=is_real,
        protocol=protocol_checks,
        channels=channel_checks,
        feature_readiness=readiness,
    )
