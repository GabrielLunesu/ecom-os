"""BackgroundRunPort — durable Hermes runs from Ecom-OS jobs (Runtime Spec §5).

A background run is always initiated from a durable Ecom-OS job; the HTTP request is not the
queue (§5.1). The worker that starts a run holds a renewable lease. Losing the lease does
NOT immediately start a duplicate run: a recovery worker first queries the known Hermes run
status and only starts a fresh attempt when the prior run is proven absent (§5.3, I-07/I-08).

A03 owns this port. The job/lease store is A02's jobs platform; until that contract lands
(IR-A03-01) this uses typed local ports + fakes (Operating Protocol §7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .bridge import HermesBridge
from .types import BackgroundRunRequest, HermesRunRef, HermesRunStatus, RunState


class RunLeaseError(RuntimeError):
    """Another worker holds the job lease and no run exists yet — do not duplicate."""


@dataclass(frozen=True)
class RunAttempt:
    job_id: str
    run_ref: HermesRunRef
    trace_id: str


class RunStore(Protocol):
    async def get_by_job(self, job_id: str) -> RunAttempt | None: ...
    async def put(self, attempt: RunAttempt) -> None: ...


class LeasePort(Protocol):
    async def acquire(self, key: str, owner: str) -> bool: ...
    async def renew(self, key: str, owner: str) -> bool: ...
    async def release(self, key: str, owner: str) -> None: ...


class FakeRunStore:
    def __init__(self) -> None:
        self._by_job: dict[str, RunAttempt] = {}

    async def get_by_job(self, job_id: str) -> RunAttempt | None:
        return self._by_job.get(job_id)

    async def put(self, attempt: RunAttempt) -> None:
        self._by_job[attempt.job_id] = attempt


class FakeLeaseStore:
    def __init__(self) -> None:
        self._held: dict[str, str] = {}

    async def acquire(self, key: str, owner: str) -> bool:
        current = self._held.get(key)
        if current is None or current == owner:
            self._held[key] = owner
            return True
        return False

    async def renew(self, key: str, owner: str) -> bool:
        return self._held.get(key) == owner

    async def release(self, key: str, owner: str) -> None:
        if self._held.get(key) == owner:
            del self._held[key]

    def force_owner(self, key: str, owner: str) -> None:
        """Test helper: simulate another worker holding the lease."""
        self._held[key] = owner


# Run states that mean "no live run is in flight" — a fresh attempt is then safe.
_TERMINAL_ABSENT = frozenset({RunState.unknown, RunState.stopped, RunState.failed})


class BackgroundRunPort:
    def __init__(self, bridge: HermesBridge, store: RunStore, leases: LeasePort) -> None:
        self._bridge = bridge
        self._store = store
        self._leases = leases

    async def start(self, request: BackgroundRunRequest, *, worker_id: str) -> HermesRunRef:
        """Start a run idempotently per ``ecom_job_id`` (I-07).

        If a run already exists for this job, return it without creating a second. Otherwise
        acquire the lease and create exactly one Hermes run.
        """
        existing = await self._store.get_by_job(request.ecom_job_id)
        if existing is not None:
            return existing.run_ref

        if not await self._leases.acquire(request.ecom_job_id, worker_id):
            # Another worker owns the job. Re-check the store: it may have just recorded a
            # run. If still none, refuse rather than risk a duplicate.
            existing = await self._store.get_by_job(request.ecom_job_id)
            if existing is not None:
                return existing.run_ref
            raise RunLeaseError(f"job {request.ecom_job_id} leased by another worker")

        ref = await self._bridge.start_run(request)
        await self._store.put(
            RunAttempt(
                job_id=request.ecom_job_id,
                run_ref=ref,
                trace_id=request.ecom_trace_id,
            )
        )
        return ref

    async def recover(self, job_id: str, *, worker_id: str) -> HermesRunStatus | None:
        """Recovery path after a lease loss / dropped stream (§5.3, §5.4).

        Query the known run status before any replacement attempt. A dropped event stream is
        never treated as failure; the status is the source of truth (I-08). Returns ``None``
        only when no run was ever recorded for the job (safe to start fresh).
        """
        existing = await self._store.get_by_job(job_id)
        if existing is None:
            return None
        return await self._bridge.get_run(existing.run_ref)

    async def start_or_recover(
        self, request: BackgroundRunRequest, *, worker_id: str
    ) -> tuple[HermesRunRef, HermesRunStatus | None]:
        """Resume safely: poll an existing run; only start a new one if none is in flight."""
        status = await self.recover(request.ecom_job_id, worker_id=worker_id)
        if status is not None and status.state not in _TERMINAL_ABSENT:
            existing = await self._store.get_by_job(request.ecom_job_id)
            assert existing is not None
            return existing.run_ref, status
        ref = await self.start(request, worker_id=worker_id)
        return ref, status

    async def stop(self, job_id: str) -> None:
        existing = await self._store.get_by_job(job_id)
        if existing is not None:
            await self._bridge.stop_run(existing.run_ref)
