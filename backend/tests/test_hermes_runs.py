"""Tests for BackgroundRunPort (Runtime Spec §5.3/§5.4, AGENTS I-07/I-08).

Proves: one run per job (idempotent, no duplicate), lease-loss recovery polls known status
instead of inferring failure, and a dropped stream is recovered by status.
"""

from __future__ import annotations

import pytest

from app.hermes.fake import FakeHermesTransport
from app.hermes.runs import (
    BackgroundRunPort,
    FakeLeaseStore,
    FakeRunStore,
    RunLeaseError,
)
from app.hermes.types import BackgroundRunRequest, RunState


def _request(job_id: str = "job_1") -> BackgroundRunRequest:
    return BackgroundRunRequest(
        ecom_trace_id="trc_1",
        ecom_job_id=job_id,
        workflow="ticket_triage.v1",
        hermes_profile_id="hp_1",
        prompt="triage this ticket",
    )


def _port() -> tuple[BackgroundRunPort, FakeHermesTransport, FakeLeaseStore]:
    bridge = FakeHermesTransport()
    leases = FakeLeaseStore()
    return BackgroundRunPort(bridge, FakeRunStore(), leases), bridge, leases


@pytest.mark.asyncio
async def test_start_is_idempotent_per_job_no_duplicate_run() -> None:
    port, _bridge, _ = _port()
    ref1 = await port.start(_request(), worker_id="w1")
    ref2 = await port.start(_request(), worker_id="w1")
    assert ref1.run_id == ref2.run_id  # same run, not a duplicate (I-07)


@pytest.mark.asyncio
async def test_lease_held_by_other_worker_refuses_when_no_run_yet() -> None:
    port, _bridge, leases = _port()
    leases.force_owner("job_1", "other_worker")
    with pytest.raises(RunLeaseError):
        await port.start(_request(), worker_id="w1")


@pytest.mark.asyncio
async def test_recover_polls_status_instead_of_starting_new_run() -> None:
    port, bridge, leases = _port()
    ref = await port.start(_request(), worker_id="w1")

    # Simulate lease loss: a different worker takes the job lease.
    leases.force_owner("job_1", "w2")

    # The recovery worker queries known status — it must NOT start a second run.
    status = await port.recover("job_1", worker_id="w2")
    assert status is not None
    assert status.ref.run_id == ref.run_id
    assert status.state is RunState.running  # polled, not inferred


@pytest.mark.asyncio
async def test_dropped_stream_recovered_by_status() -> None:
    port, bridge, _ = _port()
    ref = await port.start(_request(), worker_id="w1")
    # The stream "dropped"; the run actually completed server-side.
    bridge.force_complete_run(ref)
    status = await port.recover("job_1", worker_id="w1")
    assert status is not None
    assert status.state is RunState.completed  # recovered by polling, not failure-inferred


@pytest.mark.asyncio
async def test_recover_unknown_job_returns_none_safe_to_start() -> None:
    port, _bridge, _ = _port()
    assert await port.recover("never_started", worker_id="w1") is None


@pytest.mark.asyncio
async def test_start_or_recover_resumes_in_flight_run() -> None:
    port, _bridge, leases = _port()
    ref = await port.start(_request(), worker_id="w1")
    leases.force_owner("job_1", "w2")
    resumed_ref, status = await port.start_or_recover(_request(), worker_id="w2")
    assert resumed_ref.run_id == ref.run_id  # resumed the same run, no duplicate
    assert status is not None and status.state is RunState.running


@pytest.mark.asyncio
async def test_stop_run() -> None:
    port, bridge, _ = _port()
    ref = await port.start(_request(), worker_id="w1")
    await port.stop("job_1")
    assert (await bridge.get_run(ref)).state is RunState.stopped
