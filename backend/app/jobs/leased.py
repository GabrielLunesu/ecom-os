"""Postgres-backed leased jobs with reclaim and bounded retry."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.events import DurableJob


class JobLeaseError(RuntimeError):
    """Raised when a worker no longer owns a job lease."""


async def enqueue_job(
    session: AsyncSession,
    *,
    job_type: str,
    payload: dict[str, Any],
    deduplication_key: str = "",
    concurrency_key: str | None = None,
    trace_id: UUID | None = None,
    schema_version: int = 1,
    max_attempts: int = 3,
    next_run_at: datetime | None = None,
) -> tuple[DurableJob, bool]:
    """Create or reuse a queued job by job type and deduplication key."""

    if deduplication_key:
        existing = (
            await session.exec(
                select(DurableJob)
                .where(DurableJob.job_type == job_type)
                .where(DurableJob.deduplication_key == deduplication_key)
            )
        ).first()
        if existing is not None:
            return existing, False

    job = DurableJob(
        job_type=job_type,
        schema_version=schema_version,
        payload=payload,
        deduplication_key=deduplication_key,
        concurrency_key=concurrency_key,
        trace_id=trace_id,
        max_attempts=max_attempts,
        next_run_at=next_run_at or utcnow(),
    )
    session.add(job)
    await session.flush()
    return job, True


async def claim_jobs(
    session: AsyncSession,
    *,
    worker_id: str,
    job_type: str | None = None,
    limit: int = 1,
    lease_seconds: int = 60,
) -> list[DurableJob]:
    """Claim runnable jobs for a worker.

    SQLite test runs cannot express `FOR UPDATE SKIP LOCKED`; integration Postgres
    wiring will add row-locking. The state transitions and constraints still match
    the v2 lease contract.
    """

    now = utcnow()
    statement = (
        select(DurableJob)
        .where(col(DurableJob.state).in_(["queued", "failed_retryable", "leased"]))
        .where(DurableJob.next_run_at <= now)
        .order_by(col(DurableJob.created_at))
    )
    if job_type is not None:
        statement = statement.where(DurableJob.job_type == job_type)
    candidates = list((await session.exec(statement)).all())
    active_concurrency = {
        job.concurrency_key
        for job in candidates
        if job.state == "leased"
        and job.lease_expires_at is not None
        and job.lease_expires_at > now
        and job.concurrency_key
    }

    claimed: list[DurableJob] = []
    for job in candidates:
        if len(claimed) >= limit:
            break
        if (
            job.state == "leased"
            and job.lease_expires_at is not None
            and job.lease_expires_at > now
        ):
            continue
        if job.concurrency_key and job.concurrency_key in active_concurrency:
            continue
        job.state = "leased"
        job.lease_owner = worker_id
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.heartbeat_at = now
        job.attempts += 1
        job.updated_at = now
        if job.concurrency_key:
            active_concurrency.add(job.concurrency_key)
        session.add(job)
        claimed.append(job)

    await session.flush()
    return claimed


def _assert_owner(job: DurableJob, worker_id: str) -> None:
    if job.state != "leased" or job.lease_owner != worker_id:
        raise JobLeaseError("worker does not own the active job lease")


async def heartbeat_job(
    session: AsyncSession,
    job: DurableJob,
    *,
    worker_id: str,
    lease_seconds: int = 60,
) -> DurableJob:
    """Extend an active job lease."""

    _assert_owner(job, worker_id)
    now = utcnow()
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    job.updated_at = now
    session.add(job)
    await session.flush()
    return job


async def complete_job(session: AsyncSession, job: DurableJob, *, worker_id: str) -> DurableJob:
    """Mark a leased job complete."""

    _assert_owner(job, worker_id)
    now = utcnow()
    job.state = "succeeded"
    job.completed_at = now
    job.lease_owner = None
    job.lease_expires_at = None
    job.updated_at = now
    session.add(job)
    await session.flush()
    return job


async def fail_job(
    session: AsyncSession,
    job: DurableJob,
    *,
    worker_id: str,
    error_code: str,
    error: str,
    retryable: bool,
    retry_delay_seconds: int = 0,
) -> DurableJob:
    """Release a failed lease into retry or dead-letter state."""

    _assert_owner(job, worker_id)
    now = utcnow()
    job.last_error_code = error_code
    job.last_error = error
    job.lease_owner = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.updated_at = now
    if retryable and job.attempts < job.max_attempts:
        job.state = "failed_retryable"
        job.next_run_at = now + timedelta(seconds=max(0, retry_delay_seconds))
    else:
        job.state = "dead_letter"
    session.add(job)
    await session.flush()
    return job
