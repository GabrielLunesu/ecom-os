"""Unified conformance suite + readiness gate (Runtime Spec §15).

Runs the protocol conformance (and optionally a channel conformance) against any
``HermesBridge`` and combines the results with capability negotiation into a per-feature
readiness gate (§15.6): a required conformance failure, a missing mandatory flag, or a
fixture probe all set the dependent feature to ``not_ready``. Failures are actionable and
surfaced in ``/agents`` / System health.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.tools.catalog import CATALOG, ToolCatalog, ToolDefinition
from app.tools.envelope import (
    InvocationContext,
    SchemaMismatchError,
    ToolInvocation,
    UnknownToolError,
    redact,
    validate_invocation,
)
from app.tools.generators import to_adapter_registration, to_mcp_tools

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
    tools: tuple[CheckResult, ...] = ()
    feature_readiness: dict[str, FeatureReadiness] = field(default_factory=dict)

    @property
    def protocol_passed(self) -> bool:
        return all(c.passed for c in self.protocol)

    @property
    def channels_passed(self) -> bool:
        return all(c.passed for c in self.channels)

    @property
    def tools_passed(self) -> bool:
        return all(c.passed for c in self.tools)

    @property
    def passed(self) -> bool:
        return self.protocol_passed and self.channels_passed and self.tools_passed

    def failures(self) -> list[CheckResult]:
        return [
            c for c in (*self.protocol, *self.channels, *self.tools) if not c.passed
        ]


def _check(name: str, fn: Callable[[], bool]) -> CheckResult:
    try:
        return CheckResult(name=name, passed=bool(fn()))
    except Exception as exc:  # noqa: BLE001 - a failing check is recorded, never raised
        return CheckResult(name=name, passed=False, detail=str(exc))


def run_tool_conformance(catalog: ToolCatalog = CATALOG) -> tuple[CheckResult, ...]:
    """Tool-catalog conformance (Runtime §15.2). Real Ecom-OS evidence, no Hermes needed.

    These checks exercise the canonical catalog, the generated surfaces, and the
    pre-execution validation. They pass on real code regardless of whether a Hermes runtime
    exists, so they are honest evidence that the tool contract holds.
    """
    sample = catalog.get("ecom.order.get")

    def _catalog_discoverable() -> bool:
        return bool(catalog.names) and catalog.compatibility_hash.startswith("sha256:")

    def _adapter_mcp_parity() -> bool:
        mcp_names = {t.name for t in to_mcp_tools(catalog)}
        adapter = {r["name"]: r["schema_hash"] for r in to_adapter_registration(catalog)}
        mcp_hashes = {
            t.name: (t.meta or {}).get("ecom_schema_hash") for t in to_mcp_tools(catalog)
        }
        return mcp_names == set(adapter) == set(catalog.names) and adapter == mcp_hashes

    def _good_invocation_validates() -> bool:
        if sample is None:
            return False
        validate_invocation(catalog, _invocation(sample))
        return True

    def _unknown_tool_rejected() -> bool:
        try:
            validate_invocation(catalog, _invocation(sample, tool_name="ecom.nope.get"))
        except UnknownToolError:
            return True
        return False

    def _stale_version_rejected() -> bool:
        try:
            validate_invocation(catalog, _invocation(sample, tool_version="9.9.9"))
        except SchemaMismatchError:
            return True
        return False

    def _schema_hash_mismatch_rejected() -> bool:
        try:
            validate_invocation(catalog, _invocation(sample, schema_hash="sha256:bad"))
        except SchemaMismatchError:
            return True
        return False

    def _secrets_absent() -> bool:
        if sample is None or not sample.sensitive_fields:
            return True
        field = sample.sensitive_fields[0]
        masked = redact(sample, {field: "leak@example.com"})
        return masked[field] == "[redacted]"

    return (
        _check("catalog_discoverable", _catalog_discoverable),
        _check("adapter_mcp_parity", _adapter_mcp_parity),
        _check("good_invocation_validates", _good_invocation_validates),
        _check("unknown_tool_rejected", _unknown_tool_rejected),
        _check("stale_version_rejected", _stale_version_rejected),
        _check("schema_hash_mismatch_rejected", _schema_hash_mismatch_rejected),
        _check("secrets_absent_from_results", _secrets_absent),
    )


def _invocation(
    definition: ToolDefinition | None,
    *,
    tool_name: str | None = None,
    tool_version: str | None = None,
    schema_hash: str | None = None,
) -> ToolInvocation:
    return ToolInvocation(
        invocation_id="conf_inv",
        tool_name=tool_name or (definition.name if definition else "ecom.order.get"),
        tool_version=tool_version or (definition.version if definition else "1.0.0"),
        schema_hash=schema_hash
        or (definition.schema_hash if definition else "sha256:x"),
        arguments={"store_id": "st_1", "order_id": "ord_1"},
        context=InvocationContext(),
    )


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

    # Tool-catalog conformance (§15.2) is real Ecom-OS evidence, independent of Hermes.
    tool_checks = run_tool_conformance()

    protocol_ok = all(c.passed for c in protocol_checks)
    channels_ok = all(c.passed for c in channel_checks)
    tools_ok = all(c.passed for c in tool_checks)

    readiness: dict[str, FeatureReadiness] = {}
    for feature in FEATURE_REQUIREMENTS:
        evaluation = evaluate_feature(capabilities, feature)
        result = evaluation.readiness
        if not is_real:
            # A fixture probe never proves the production contract (I-19, §15.6).
            result = FeatureReadiness.not_ready
        elif feature in _PROTOCOL_FEATURES and not protocol_ok:
            result = FeatureReadiness.not_ready
        elif feature == "external_tools" and not tools_ok:
            # A broken tool contract blocks the tools feature even with a real Hermes.
            result = FeatureReadiness.not_ready
        elif feature == "channels" and channel_checks and not channels_ok:
            result = FeatureReadiness.not_ready
        readiness[feature] = result

    return ConformanceReport(
        is_real=is_real,
        protocol=protocol_checks,
        channels=channel_checks,
        tools=tool_checks,
        feature_readiness=readiness,
    )
