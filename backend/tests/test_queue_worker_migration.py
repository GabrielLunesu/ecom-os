# ruff: noqa: INP001
"""Queue worker migration-mode tests for durable webhook dispatch rollout."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services import queue_worker
from app.services.queue import QueuedTask


@pytest.mark.asyncio
async def test_queue_worker_legacy_mode_uses_redis_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue_worker.settings, "webhook_dispatch_worker_mode", "legacy")
    monkeypatch.setattr(queue_worker.settings, "rq_dispatch_throttle_seconds", 0)

    durable_calls: list[bool] = []

    async def _durable() -> int:
        durable_calls.append(True)
        return 1

    async def _legacy_handler(task: QueuedTask) -> None:
        del task

    tasks = [
        QueuedTask(
            task_type=queue_worker.WEBHOOK_TASK_TYPE,
            payload={},
            created_at=datetime.now(UTC),
            attempts=0,
        ),
        None,
    ]

    def _dequeue(*args: object, **kwargs: object) -> QueuedTask | None:
        del args, kwargs
        return tasks.pop(0)

    monkeypatch.setattr(queue_worker, "flush_durable_webhook_jobs", _durable)
    monkeypatch.setitem(
        queue_worker._TASK_HANDLERS,
        queue_worker.WEBHOOK_TASK_TYPE,
        queue_worker._TaskHandler(
            handler=_legacy_handler,
            attempts_to_delay=lambda attempts: float(attempts),
            requeue=lambda task, delay: True,
        ),
    )
    monkeypatch.setattr(queue_worker, "dequeue_task", _dequeue)

    assert await queue_worker.flush_queue() == 1
    assert durable_calls == []


@pytest.mark.asyncio
async def test_queue_worker_durable_mode_skips_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue_worker.settings, "webhook_dispatch_worker_mode", "durable")
    monkeypatch.setattr(queue_worker.settings, "rq_dispatch_throttle_seconds", 0)

    durable_calls: list[bool] = []
    dequeued: list[bool] = []

    async def _durable() -> int:
        durable_calls.append(True)
        return 2

    def _dequeue(*args: object, **kwargs: object) -> QueuedTask | None:
        del args, kwargs
        dequeued.append(True)
        return None

    monkeypatch.setattr(queue_worker, "flush_durable_webhook_jobs", _durable)
    monkeypatch.setattr(queue_worker, "dequeue_task", _dequeue)

    assert await queue_worker.flush_queue() == 2
    assert durable_calls == [True]
    assert dequeued == []


@pytest.mark.asyncio
async def test_queue_worker_dual_mode_processes_durable_then_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue_worker.settings, "webhook_dispatch_worker_mode", "dual")
    monkeypatch.setattr(queue_worker.settings, "rq_dispatch_throttle_seconds", 0)

    calls: list[str] = []

    async def _durable() -> int:
        calls.append("durable")
        return 1

    async def _legacy_handler(task: QueuedTask) -> None:
        del task
        calls.append("legacy")

    tasks = [
        QueuedTask(
            task_type=queue_worker.WEBHOOK_TASK_TYPE,
            payload={},
            created_at=datetime.now(UTC),
            attempts=0,
        ),
        None,
    ]

    def _dequeue(*args: object, **kwargs: object) -> QueuedTask | None:
        del args, kwargs
        return tasks.pop(0)

    monkeypatch.setattr(queue_worker, "flush_durable_webhook_jobs", _durable)
    monkeypatch.setitem(
        queue_worker._TASK_HANDLERS,
        queue_worker.WEBHOOK_TASK_TYPE,
        queue_worker._TaskHandler(
            handler=_legacy_handler,
            attempts_to_delay=lambda attempts: float(attempts),
            requeue=lambda task, delay: True,
        ),
    )
    monkeypatch.setattr(queue_worker, "dequeue_task", _dequeue)

    assert await queue_worker.flush_queue() == 2
    assert calls == ["durable", "legacy"]


@pytest.mark.asyncio
async def test_queue_worker_invalid_mode_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue_worker.settings, "webhook_dispatch_worker_mode", "bad-mode")
    monkeypatch.setattr(queue_worker.settings, "rq_dispatch_throttle_seconds", 0)

    durable_calls: list[bool] = []

    async def _durable() -> int:
        durable_calls.append(True)
        return 1

    tasks = [None]

    def _dequeue(*args: object, **kwargs: object) -> QueuedTask | None:
        del args, kwargs
        return tasks.pop(0)

    monkeypatch.setattr(queue_worker, "flush_durable_webhook_jobs", _durable)
    monkeypatch.setattr(queue_worker, "dequeue_task", _dequeue)

    assert await queue_worker.flush_queue() == 0
    assert durable_calls == []


@pytest.mark.asyncio
async def test_queue_worker_durable_mode_idles_when_blocking_without_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(queue_worker.settings, "webhook_dispatch_worker_mode", "durable")

    sleeps: list[float] = []

    async def _durable() -> int:
        return 0

    async def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(queue_worker, "flush_durable_webhook_jobs", _durable)
    monkeypatch.setattr(queue_worker.asyncio, "sleep", _sleep)

    assert await queue_worker.flush_queue(block=True, block_timeout=3.0) == 0
    assert sleeps == [3.0]
