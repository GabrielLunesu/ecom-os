"""Capability flags, feature requirements, and the compatibility record (Runtime §3).

Each product surface declares its required flags. A missing optional flag degrades only
that surface; a missing mandatory flag prevents the feature from reaching ``ready`` (AGENTS
I-19). The probe writes a visible ``CompatibilityRecord``; nothing here assumes an endpoint
exists from a version string alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .types import HermesCapabilities

# The v1 capability model (Runtime §3.2).
REQUIRED_FLAGS: tuple[str, ...] = (
    "interactive.json_rpc",
    "interactive.session_create",
    "interactive.session_resume",
    "interactive.session_history",
    "interactive.streaming",
    "interactive.tool_events",
    "interactive.interrupt",
    "interactive.branch",
    "interactive.approval_response",
    "background.runs",
    "background.events",
    "background.stop",
    "background.approval_response",
    "external_tools.adapter",
    "external_tools.mcp",
    "telemetry.tool_hooks",
    "telemetry.session_hooks",
    "channels.delivery",
    "cron.scheduling",
)


@dataclass(frozen=True)
class FeatureRequirement:
    """Flags a feature needs. Missing mandatory → not_ready; missing optional → degraded."""

    feature: str
    mandatory: frozenset[str]
    optional: frozenset[str] = frozenset()


FEATURE_REQUIREMENTS: dict[str, FeatureRequirement] = {
    "main_chat": FeatureRequirement(
        feature="main_chat",
        mandatory=frozenset(
            {
                "interactive.json_rpc",
                "interactive.session_create",
                "interactive.session_resume",
                "interactive.session_history",
                "interactive.streaming",
                "interactive.tool_events",
                "interactive.interrupt",
            }
        ),
        optional=frozenset({"interactive.branch", "interactive.approval_response"}),
    ),
    "background_runs": FeatureRequirement(
        feature="background_runs",
        mandatory=frozenset(
            {"background.runs", "background.events", "background.stop"}
        ),
        optional=frozenset({"background.approval_response"}),
    ),
    "external_tools": FeatureRequirement(
        feature="external_tools",
        # Either adapter or MCP suffices in principle, but v1 requires at least MCP as the
        # portable surface; adapter is the optional richer path.
        mandatory=frozenset({"external_tools.mcp"}),
        optional=frozenset({"external_tools.adapter", "telemetry.tool_hooks"}),
    ),
    "channels": FeatureRequirement(
        feature="channels",
        mandatory=frozenset({"channels.delivery"}),
        optional=frozenset({"cron.scheduling"}),
    ),
}


class FeatureReadiness(str, Enum):
    ready = "ready"
    degraded = "degraded"
    not_ready = "not_ready"


@dataclass(frozen=True)
class FeatureEvaluation:
    feature: str
    readiness: FeatureReadiness
    missing_mandatory: tuple[str, ...]
    missing_optional: tuple[str, ...]


def evaluate_feature(
    capabilities: HermesCapabilities, feature: str
) -> FeatureEvaluation:
    """Resolve a feature's readiness against probed capabilities (Runtime §3.2)."""
    requirement = FEATURE_REQUIREMENTS.get(feature)
    if requirement is None:
        raise KeyError(f"unknown feature: {feature!r}")
    missing_mandatory = tuple(
        sorted(f for f in requirement.mandatory if not capabilities.has(f))
    )
    missing_optional = tuple(
        sorted(f for f in requirement.optional if not capabilities.has(f))
    )
    if missing_mandatory:
        readiness = FeatureReadiness.not_ready
    elif missing_optional:
        readiness = FeatureReadiness.degraded
    else:
        readiness = FeatureReadiness.ready
    return FeatureEvaluation(
        feature=feature,
        readiness=readiness,
        missing_mandatory=missing_mandatory,
        missing_optional=missing_optional,
    )


@dataclass(frozen=True)
class ConformanceResult:
    passed: bool
    checks: tuple[tuple[str, bool], ...] = ()
    detail: str | None = None


@dataclass(frozen=True)
class CompatibilityRecord:
    """Visible startup/upgrade record (Runtime §3.1).

    ``is_real`` is False whenever the record came from a fake transport, so the system can
    refuse to mark Hermes-dependent features ``ready`` without a real probe (AGENTS I-19).
    """

    hermes_version: str | None
    profile_fingerprint: str | None
    enabled_transports: tuple[str, ...]
    capabilities: HermesCapabilities
    adapter_name: str | None
    adapter_version: str | None
    mcp_catalog_version: str | None
    mcp_compatibility_hash: str | None
    conformance: ConformanceResult
    probed_at: str
    is_real: bool = False
    features: dict[str, FeatureEvaluation] = field(default_factory=dict)

    def feature_readiness(self, feature: str) -> FeatureReadiness:
        evaluation = self.features.get(feature) or evaluate_feature(
            self.capabilities, feature
        )
        if not self.is_real:
            # A fixture probe never proves the production contract.
            return FeatureReadiness.not_ready
        return evaluation.readiness
