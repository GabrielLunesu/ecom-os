"""Conformance tests for the HermesBridge contract against the fake transport.

These mirror Runtime Spec §15.1 (protocol) and §3.2 (capability negotiation) at fixture
scale. They prove the bridge shape — ordered streaming, resume/history, interrupt, branch,
background poll-not-infer — and that a fixture probe never promotes a feature to ``ready``.
"""

from __future__ import annotations

import pytest

from app.hermes.bridge import HermesBridge
from app.hermes.capabilities import (
    REQUIRED_FLAGS,
    FeatureReadiness,
    evaluate_feature,
)
from app.hermes.fake import FakeHermesTransport
from app.hermes.probe import capability_probe
from app.hermes.types import (
    BackgroundRunRequest,
    BranchRequest,
    CreateSession,
    HermesCapabilities,
    HermesEventType,
    InteractivePrompt,
    InterruptRequest,
    RunState,
    SessionQuery,
    SessionState,
)


def test_fake_satisfies_bridge_protocol() -> None:
    assert isinstance(FakeHermesTransport(), HermesBridge)


# --- interactive sessions ----------------------------------------------------
@pytest.mark.asyncio
async def test_create_list_resume_history_roundtrip() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.create_session(CreateSession(profile_id="hp1", title="t"))

    page = await bridge.list_sessions(SessionQuery(profile_id="hp1"))
    assert ref.session_id in {s.ref.session_id for s in page.items}

    # Drive one turn so there is history to resume.
    async for _ in bridge.submit_prompt(InteractivePrompt(ref=ref, text="hi")):
        pass

    resumed = await bridge.create_session(
        CreateSession(profile_id="hp1", resume_session_id=ref.session_id)
    )
    assert resumed.session_id == ref.session_id  # same canonical session, not a copy
    history = await bridge.get_history(resumed)
    assert [m.role for m in history.messages] == ["user", "assistant"]
    assert history.source == "hermes"


@pytest.mark.asyncio
async def test_submit_prompt_streams_ordered_and_finalizes() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.create_session(CreateSession(profile_id="hp1"))

    events = [e async for e in bridge.submit_prompt(InteractivePrompt(ref=ref, text="q"))]
    seqs = [e.seq for e in events]
    assert seqs == sorted(seqs)
    assert events[-1].type is HermesEventType.final
    assert any(e.type is HermesEventType.tool_start for e in events)

    status = await bridge.get_status(ref)
    assert status.state is SessionState.idle


@pytest.mark.asyncio
async def test_interrupt_yields_interrupted_terminal_not_final() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.create_session(CreateSession(profile_id="hp1"))

    seen: list[HermesEventType] = []
    stream = bridge.submit_prompt(InteractivePrompt(ref=ref, text="long task"))
    first = await stream.__anext__()
    seen.append(first.type)
    # User cancels after the first event; the next boundary must surface interrupted.
    await bridge.interrupt(InterruptRequest(ref=ref))
    async for event in stream:
        seen.append(event.type)

    assert HermesEventType.interrupted in seen
    assert HermesEventType.final not in seen
    status = await bridge.get_status(ref)
    assert status.state is SessionState.interrupted
    # No assistant message was committed because the turn was interrupted.
    history = await bridge.get_history(ref)
    assert [m.role for m in history.messages] == ["user"]


@pytest.mark.asyncio
async def test_branch_creates_new_session_with_copied_history() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.create_session(CreateSession(profile_id="hp1"))
    async for _ in bridge.submit_prompt(InteractivePrompt(ref=ref, text="hi")):
        pass

    branched = await bridge.branch(BranchRequest(ref=ref))
    assert branched.session_id != ref.session_id
    branched_history = await bridge.get_history(branched)
    original_history = await bridge.get_history(ref)
    assert len(branched_history.messages) == len(original_history.messages)


# --- background runs: poll, never infer (Runtime §5.4, §13.3) ----------------
@pytest.mark.asyncio
async def test_background_run_stream_and_status() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.start_run(
        BackgroundRunRequest(
            ecom_trace_id="trc1",
            ecom_job_id="job1",
            workflow="ticket_triage.v1",
            hermes_profile_id="hp1",
            prompt="triage",
        )
    )
    events = [e async for e in bridge.stream_run(ref)]
    assert events[-1].type is HermesEventType.final
    status = await bridge.get_run(ref)
    assert status.state is RunState.completed


@pytest.mark.asyncio
async def test_dropped_stream_is_recovered_by_polling_not_inference() -> None:
    """A lost stream must not be read as failure; status is the source of truth."""
    bridge = FakeHermesTransport()
    ref = await bridge.start_run(
        BackgroundRunRequest(
            ecom_trace_id="trc1",
            ecom_job_id="job1",
            workflow="research.v1",
            hermes_profile_id="hp1",
            prompt="go",
        )
    )
    # Simulate: we never consumed the stream (it "dropped"). Status still says running.
    assert (await bridge.get_run(ref)).state is RunState.running
    # The run actually finished server-side; polling reveals it — we did not infer failure.
    bridge.force_complete_run(ref)
    assert (await bridge.get_run(ref)).state is RunState.completed


@pytest.mark.asyncio
async def test_stop_run() -> None:
    bridge = FakeHermesTransport()
    ref = await bridge.start_run(
        BackgroundRunRequest(
            ecom_trace_id="t",
            ecom_job_id="j",
            workflow="w",
            hermes_profile_id="hp1",
            prompt="p",
        )
    )
    await bridge.stop_run(ref)
    assert (await bridge.get_run(ref)).state is RunState.stopped


# --- capability negotiation (Runtime §3.2) -----------------------------------
def test_evaluate_feature_full_ready() -> None:
    caps = HermesCapabilities(flags=frozenset(REQUIRED_FLAGS))
    assert evaluate_feature(caps, "main_chat").readiness is FeatureReadiness.ready


def test_missing_mandatory_flag_blocks_feature() -> None:
    caps = HermesCapabilities(flags=frozenset(REQUIRED_FLAGS) - {"interactive.interrupt"})
    evaluation = evaluate_feature(caps, "main_chat")
    assert evaluation.readiness is FeatureReadiness.not_ready
    assert "interactive.interrupt" in evaluation.missing_mandatory


def test_missing_only_optional_flag_degrades_feature() -> None:
    caps = HermesCapabilities(flags=frozenset(REQUIRED_FLAGS) - {"interactive.branch"})
    evaluation = evaluate_feature(caps, "main_chat")
    assert evaluation.readiness is FeatureReadiness.degraded
    assert "interactive.branch" in evaluation.missing_optional


# --- the probe (Runtime §3.1, AGENTS I-19) -----------------------------------
@pytest.mark.asyncio
async def test_probe_passes_conformance_but_fixture_is_not_ready() -> None:
    bridge = FakeHermesTransport()
    record = await capability_probe(
        bridge,
        probed_at="2026-06-19T00:00:00Z",
        mcp_catalog_version="1.0.0",
        is_real=False,  # fixture
    )
    assert record.conformance.passed is True
    # Even with a passing fixture conformance, no feature is "ready" without a real probe.
    assert record.feature_readiness("main_chat") is FeatureReadiness.not_ready


@pytest.mark.asyncio
async def test_real_probe_with_full_flags_is_ready() -> None:
    bridge = FakeHermesTransport()
    record = await capability_probe(
        bridge,
        probed_at="2026-06-19T00:00:00Z",
        is_real=True,  # stand-in for a genuine pinned Hermes
    )
    assert record.feature_readiness("main_chat") is FeatureReadiness.ready


@pytest.mark.asyncio
async def test_real_probe_missing_channel_flag_blocks_only_that_feature() -> None:
    reduced = frozenset(REQUIRED_FLAGS) - {"channels.delivery"}
    bridge = FakeHermesTransport(flags=reduced)
    record = await capability_probe(bridge, probed_at="t", is_real=True)
    assert record.feature_readiness("main_chat") is FeatureReadiness.ready
    assert record.feature_readiness("channels") is FeatureReadiness.not_ready
