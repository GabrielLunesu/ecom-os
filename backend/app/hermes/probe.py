"""Capability probe and harmless conformance run (Runtime Spec §3.3, §15).

The probe uses supported health/capability endpoints and a harmless conformance run with no
real store side effect, then writes a ``CompatibilityRecord``. Version-string comparison
alone is never sufficient (AGENTS I-19). A probe against a fake transport yields
``is_real=False``.
"""

from __future__ import annotations

from .bridge import HermesBridge
from .capabilities import (
    FEATURE_REQUIREMENTS,
    CompatibilityRecord,
    ConformanceResult,
    evaluate_feature,
)
from .types import (
    BranchRequest,
    CreateSession,
    HermesCapabilities,
    HermesEventType,
    InteractivePrompt,
    InterruptRequest,
)

# A profile reserved for the harmless probe conversation (no business side effect).
_PROBE_PROFILE = "hp_probe"


async def run_conformance(bridge: HermesBridge) -> ConformanceResult:
    """Exercise the interactive protocol once and report ordered per-check results.

    Mirrors Runtime §15.1 protocol tests at fixture scale: create → submit → ordered
    stream → history → branch → interrupt. No store mutation occurs.
    """
    checks: list[tuple[str, bool]] = []

    try:
        ref = await bridge.create_session(CreateSession(profile_id=_PROBE_PROFILE))
    except Exception:  # noqa: BLE001 - a transport that cannot create a session fails honestly
        # Record the failure rather than crashing; an unconfigured/blocked transport (e.g.
        # the native stub) reports not-passed conformance, never a fabricated pass.
        checks.append(("session_create", False))
        return ConformanceResult(passed=False, checks=tuple(checks))
    checks.append(("session_create", bool(ref.session_id)))

    seqs: list[int] = []
    saw_final = False
    async for event in bridge.submit_prompt(InteractivePrompt(ref=ref, text="ping")):
        seqs.append(event.seq)
        if event.type is HermesEventType.final:
            saw_final = True
    checks.append(("streaming_ordered", seqs == sorted(seqs) and len(seqs) > 0))
    checks.append(("stream_terminates_final", saw_final))

    history = await bridge.get_history(ref)
    checks.append(("history_retrievable", len(history.messages) >= 2))

    try:
        branched = await bridge.branch(BranchRequest(ref=ref))
        checks.append(("branch", branched.session_id != ref.session_id))
    except Exception:  # noqa: BLE001 - branch is optional; record honestly
        checks.append(("branch", False))

    # Interrupt then run again; the stream must surface an interrupted terminal, not final.
    await bridge.interrupt(InterruptRequest(ref=ref))
    interrupted = False
    async for event in bridge.submit_prompt(InteractivePrompt(ref=ref, text="again")):
        if event.type is HermesEventType.interrupted:
            interrupted = True
            break
        if event.type is HermesEventType.final:
            break
    checks.append(("interrupt", interrupted))

    passed = all(ok for _, ok in checks)
    return ConformanceResult(passed=passed, checks=tuple(checks))


async def capability_probe(
    bridge: HermesBridge,
    *,
    probed_at: str,
    adapter_name: str | None = None,
    adapter_version: str | None = None,
    mcp_catalog_version: str | None = None,
    mcp_compatibility_hash: str | None = None,
    is_real: bool = False,
    profile_fingerprint: str | None = None,
) -> CompatibilityRecord:
    """Run the probe and build the visible compatibility record (Runtime §3.1).

    ``is_real`` MUST be True only when probing a genuine pinned Hermes release. The default
    False keeps fixture probes from promoting features to ``ready`` (AGENTS I-19).
    """
    health = await bridge.health()
    capabilities: HermesCapabilities = await bridge.probe()
    conformance = await run_conformance(bridge)

    features = {
        name: evaluate_feature(capabilities, name) for name in FEATURE_REQUIREMENTS
    }

    return CompatibilityRecord(
        hermes_version=health.version,
        profile_fingerprint=profile_fingerprint,
        enabled_transports=("interactive.json_rpc", "background.runs"),
        capabilities=capabilities,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        mcp_catalog_version=mcp_catalog_version,
        mcp_compatibility_hash=mcp_compatibility_hash,
        conformance=conformance,
        probed_at=probed_at,
        is_real=is_real,
        features=features,
    )
