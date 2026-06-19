# ruff: noqa: INP001
"""Webhook queue and dispatch worker tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401 - ensure SQLModel metadata is fully registered
from app.core.time import utcnow
from app.jobs.leased import claim_jobs, enqueue_job
from app.models.board_webhook_payloads import BoardWebhookPayload
from app.models.board_webhooks import BoardWebhook
from app.models.boards import Board
from app.models.events import DurableJob
from app.models.gateways import Gateway
from app.models.organizations import Organization
from app.services.webhooks import dispatch
from app.services.webhooks.queue import (
    QueuedInboundDelivery,
    dequeue_webhook_delivery,
    enqueue_webhook_delivery,
    requeue_if_failed,
)


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_webhook_payload(
    session: AsyncSession,
) -> tuple[Board, BoardWebhook, BoardWebhookPayload]:
    organization_id = uuid4()
    gateway_id = uuid4()
    board_id = uuid4()
    session.add(Organization(id=organization_id, name=f"org-{organization_id}"))
    session.add(
        Gateway(
            id=gateway_id,
            organization_id=organization_id,
            name="gateway",
            url="https://gateway.example.local",
            workspace_root="/tmp/workspace",
        )
    )
    board = Board(
        id=board_id,
        organization_id=organization_id,
        gateway_id=gateway_id,
        name="Launch board",
        slug="launch-board",
        description="Board for launch automation.",
    )
    webhook = BoardWebhook(
        id=uuid4(),
        board_id=board.id,
        description="Triage payload.",
        enabled=True,
    )
    payload = BoardWebhookPayload(
        id=uuid4(),
        board_id=board.id,
        webhook_id=webhook.id,
        payload={"event": "deploy"},
        content_type="application/json",
    )
    session.add(board)
    session.add(webhook)
    session.add(payload)
    await session.flush()
    return board, webhook, payload


async def _enqueue_and_claim_webhook_job(
    session: AsyncSession,
    *,
    board_id: UUID,
    webhook_id: UUID,
    payload_id: UUID,
    worker_id: str,
    max_attempts: int = 2,
) -> DurableJob:
    job, created = await enqueue_job(
        session,
        job_type=dispatch.BOARD_WEBHOOK_DURABLE_JOB_TYPE,
        payload={
            "board_id": str(board_id),
            "webhook_id": str(webhook_id),
            "payload_id": str(payload_id),
        },
        deduplication_key=f"test:{payload_id}",
        concurrency_key=f"board:{board_id}:webhook:{webhook_id}",
        max_attempts=max_attempts,
    )
    assert created is True
    claimed = await claim_jobs(
        session,
        worker_id=worker_id,
        job_type=dispatch.BOARD_WEBHOOK_DURABLE_JOB_TYPE,
    )
    assert [item.id for item in claimed] == [job.id]
    return claimed[0]


class _FakeRedis:
    def __init__(self) -> None:
        self.values: list[str] = []

    def lpush(self, key: str, value: str) -> None:
        self.values.insert(0, value)

    def rpop(self, key: str) -> str | None:
        if not self.values:
            return None
        return self.values.pop()


@pytest.mark.parametrize("attempts", [0, 1, 2])
def test_webhook_queue_roundtrip(monkeypatch: pytest.MonkeyPatch, attempts: int) -> None:
    fake = _FakeRedis()

    def _fake_redis(*, redis_url: str | None = None) -> _FakeRedis:
        return fake

    board_id = uuid4()
    webhook_id = uuid4()
    payload_id = uuid4()
    payload = QueuedInboundDelivery(
        board_id=board_id,
        webhook_id=webhook_id,
        payload_id=payload_id,
        received_at=datetime.now(UTC),
        attempts=attempts,
    )

    monkeypatch.setattr("app.services.queue._redis_client", _fake_redis)
    assert enqueue_webhook_delivery(payload)

    dequeued = dequeue_webhook_delivery()
    assert dequeued is not None
    assert dequeued.board_id == board_id
    assert dequeued.webhook_id == webhook_id
    assert dequeued.payload_id == payload_id
    assert dequeued.attempts == attempts


def test_webhook_queue_dequeue_legacy_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()

    def _fake_redis(*, redis_url: str | None = None) -> _FakeRedis:
        return fake

    payload_id = uuid4()
    board_id = uuid4()
    webhook_id = uuid4()
    received_at = datetime.now(UTC)
    fake.values.append(
        json.dumps(
            {
                "board_id": str(board_id),
                "webhook_id": str(webhook_id),
                "payload_id": str(payload_id),
                "received_at": received_at.isoformat(),
                "attempts": 2,
            }
        )
    )

    monkeypatch.setattr("app.services.queue._redis_client", _fake_redis)
    dequeued = dequeue_webhook_delivery()

    assert dequeued is not None
    assert dequeued.board_id == board_id
    assert dequeued.webhook_id == webhook_id
    assert dequeued.payload_id == payload_id
    assert dequeued.attempts == 2


@pytest.mark.parametrize("attempts", [0, 1, 2, 3])
def test_requeue_respects_retry_cap(monkeypatch: pytest.MonkeyPatch, attempts: int) -> None:
    fake = _FakeRedis()

    def _fake_redis(*, redis_url: str | None = None) -> _FakeRedis:
        return fake

    monkeypatch.setattr("app.services.queue._redis_client", _fake_redis)

    payload = QueuedInboundDelivery(
        board_id=uuid4(),
        webhook_id=uuid4(),
        payload_id=uuid4(),
        received_at=datetime.now(UTC),
        attempts=attempts,
    )

    if attempts >= 3:
        assert requeue_if_failed(payload) is False
        assert fake.values == []
    else:
        assert requeue_if_failed(payload) is True
        requeued = dequeue_webhook_delivery()
        assert requeued is not None
        assert requeued.attempts == attempts + 1


class _FakeQueuedItem:
    def __init__(self, attempts: int = 0) -> None:
        self.payload_id = uuid4()
        self.webhook_id = uuid4()
        self.board_id = uuid4()
        self.attempts = attempts


def _patch_dequeue(
    monkeypatch: pytest.MonkeyPatch, items: list[QueuedInboundDelivery | None]
) -> None:
    def _dequeue() -> QueuedInboundDelivery | None:
        if not items:
            return None
        return items.pop(0)

    monkeypatch.setattr(dispatch, "dequeue_webhook_delivery", _dequeue)


@pytest.mark.asyncio
async def test_dispatch_flush_processes_items_and_throttles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items: list[QueuedInboundDelivery | None] = [
        _FakeQueuedItem(),
        _FakeQueuedItem(),
        None,
    ]
    _patch_dequeue(monkeypatch, items)

    processed: list[UUID] = []
    throttles: list[float] = []

    async def _process(item: QueuedInboundDelivery) -> None:
        processed.append(item.payload_id)

    monkeypatch.setattr(dispatch, "_process_single_item", _process)
    monkeypatch.setattr(dispatch.settings, "rq_dispatch_throttle_seconds", 0)
    monkeypatch.setattr(dispatch.time, "sleep", lambda seconds: throttles.append(seconds))

    await dispatch.flush_webhook_delivery_queue()

    assert len(processed) == 2
    assert throttles == [0.0, 0.0]


@pytest.mark.asyncio
async def test_dispatch_flush_requeues_on_process_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakeQueuedItem()
    _patch_dequeue(monkeypatch, [item, None])

    async def _process(_: QueuedInboundDelivery) -> None:
        raise RuntimeError("boom")

    requeued: list[QueuedInboundDelivery] = []

    def _requeue(payload: QueuedInboundDelivery) -> bool:
        requeued.append(payload)
        return True

    monkeypatch.setattr(dispatch, "_process_single_item", _process)
    monkeypatch.setattr(dispatch, "requeue_if_failed", _requeue)
    monkeypatch.setattr(dispatch.settings, "rq_dispatch_throttle_seconds", 0)
    monkeypatch.setattr(dispatch.time, "sleep", lambda seconds: None)

    await dispatch.flush_webhook_delivery_queue()

    assert len(requeued) == 1
    assert requeued[0].payload_id == item.payload_id


@pytest.mark.asyncio
async def test_dispatch_flush_recovers_from_dequeue_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakeQueuedItem()
    call_count = 0

    def _dequeue() -> QueuedInboundDelivery | None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("dequeue broken")
        if call_count == 2:
            return item
        return None

    monkeypatch.setattr(dispatch, "dequeue_webhook_delivery", _dequeue)

    processed = 0

    async def _process(_: QueuedInboundDelivery) -> None:
        nonlocal processed
        processed += 1

    monkeypatch.setattr(dispatch, "_process_single_item", _process)
    monkeypatch.setattr(dispatch.settings, "rq_dispatch_throttle_seconds", 0)
    monkeypatch.setattr(dispatch.time, "sleep", lambda seconds: None)

    await dispatch.flush_webhook_delivery_queue()

    assert call_count == 3
    assert processed == 1


@pytest.mark.asyncio
async def test_process_durable_webhook_job_completes_after_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _session() as session:
        board, webhook, payload = await _seed_webhook_payload(session)
        job = await _enqueue_and_claim_webhook_job(
            session,
            board_id=board.id,
            webhook_id=webhook.id,
            payload_id=payload.id,
            worker_id="worker-a",
        )
        notified: list[UUID] = []

        async def _notify(
            *,
            session: AsyncSession,
            board: Board,
            webhook: BoardWebhook,
            payload: BoardWebhookPayload,
        ) -> None:
            del session, board, webhook
            notified.append(payload.id)

        monkeypatch.setattr(dispatch, "_notify_target_agent", _notify)

        ok = await dispatch.process_durable_webhook_job(
            session,
            job,
            worker_id="worker-a",
        )

        assert ok is True
        assert notified == [payload.id]
        assert job.state == "succeeded"
        assert job.completed_at is not None
        assert job.lease_owner is None


@pytest.mark.asyncio
async def test_process_durable_webhook_job_retries_then_dead_letters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _session() as session:
        board, webhook, payload = await _seed_webhook_payload(session)
        job = await _enqueue_and_claim_webhook_job(
            session,
            board_id=board.id,
            webhook_id=webhook.id,
            payload_id=payload.id,
            worker_id="worker-a",
            max_attempts=2,
        )

        async def _notify(
            *,
            session: AsyncSession,
            board: Board,
            webhook: BoardWebhook,
            payload: BoardWebhookPayload,
        ) -> None:
            del session, board, webhook, payload
            raise RuntimeError("gateway unavailable")

        monkeypatch.setattr(dispatch, "_notify_target_agent", _notify)
        monkeypatch.setattr(dispatch.settings, "rq_dispatch_retry_base_seconds", 0)

        first_ok = await dispatch.process_durable_webhook_job(
            session,
            job,
            worker_id="worker-a",
        )
        assert first_ok is False
        assert job.state == "failed_retryable"
        assert job.last_error_code == "webhook_dispatch_failed"

        job.next_run_at = utcnow() - timedelta(seconds=1)
        session.add(job)
        await session.flush()
        claimed = await claim_jobs(
            session,
            worker_id="worker-b",
            job_type=dispatch.BOARD_WEBHOOK_DURABLE_JOB_TYPE,
        )
        assert [item.id for item in claimed] == [job.id]

        second_ok = await dispatch.process_durable_webhook_job(
            session,
            claimed[0],
            worker_id="worker-b",
        )

        assert second_ok is False
        assert claimed[0].state == "dead_letter"
        assert claimed[0].attempts == 2
        assert claimed[0].last_error == "gateway unavailable"


@pytest.mark.asyncio
async def test_process_durable_webhook_job_dead_letters_stale_payload() -> None:
    async with _session() as session:
        job = await _enqueue_and_claim_webhook_job(
            session,
            board_id=uuid4(),
            webhook_id=uuid4(),
            payload_id=uuid4(),
            worker_id="worker-a",
            max_attempts=3,
        )

        ok = await dispatch.process_durable_webhook_job(
            session,
            job,
            worker_id="worker-a",
        )

        assert ok is False
        assert job.state == "dead_letter"
        assert job.last_error_code == "webhook_payload_unavailable"


@pytest.mark.asyncio
async def test_notify_target_agent_prefers_mapped_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_id = uuid4()
    mapped_agent = SimpleNamespace(
        id=agent_id,
        name="Mapped Agent",
        openclaw_session_id="mapped:session",
    )
    lead_agent = SimpleNamespace(
        id=uuid4(),
        name="Lead Agent",
        openclaw_session_id="lead:session",
    )
    sent: list[dict[str, str]] = []

    class _FakeAgentObjects:
        def filter_by(self, **kwargs: object) -> _FakeAgentObjects:
            self._kwargs = kwargs
            return self

        async def first(self, session: object) -> object | None:
            del session
            if self._kwargs.get("id") == agent_id:
                return mapped_agent
            if self._kwargs.get("is_board_lead") is True:
                return lead_agent
            return None

    class _FakeDispatchService:
        def __init__(self, session: object) -> None:
            del session

        async def optional_gateway_config_for_board(self, board: object) -> object:
            del board
            return object()

        async def try_send_agent_message(
            self,
            *,
            session_key: str,
            config: object,
            agent_name: str,
            message: str,
            deliver: bool = False,
        ) -> None:
            del config, message, deliver
            sent.append({"session_key": session_key, "agent_name": agent_name})

    monkeypatch.setattr(dispatch.Agent, "objects", _FakeAgentObjects())
    monkeypatch.setattr(dispatch, "GatewayDispatchService", _FakeDispatchService)

    webhook = SimpleNamespace(id=uuid4(), description="desc", agent_id=agent_id)
    board = SimpleNamespace(id=uuid4(), name="Board")
    payload = SimpleNamespace(id=uuid4(), payload={"event": "test"})

    await dispatch._notify_target_agent(
        session=SimpleNamespace(),
        board=board,
        webhook=webhook,
        payload=payload,
    )

    assert sent == [{"session_key": "mapped:session", "agent_name": "Mapped Agent"}]


@pytest.mark.asyncio
async def test_notify_target_agent_falls_back_to_lead(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lead_agent = SimpleNamespace(
        id=uuid4(),
        name="Lead Agent",
        openclaw_session_id="lead:session",
    )
    sent: list[dict[str, str]] = []

    class _FakeAgentObjects:
        def filter_by(self, **kwargs: object) -> _FakeAgentObjects:
            self._kwargs = kwargs
            return self

        async def first(self, session: object) -> object | None:
            del session
            if self._kwargs.get("is_board_lead") is True:
                return lead_agent
            return None

    class _FakeDispatchService:
        def __init__(self, session: object) -> None:
            del session

        async def optional_gateway_config_for_board(self, board: object) -> object:
            del board
            return object()

        async def try_send_agent_message(
            self,
            *,
            session_key: str,
            config: object,
            agent_name: str,
            message: str,
            deliver: bool = False,
        ) -> None:
            del config, message, deliver
            sent.append({"session_key": session_key, "agent_name": agent_name})

    monkeypatch.setattr(dispatch.Agent, "objects", _FakeAgentObjects())
    monkeypatch.setattr(dispatch, "GatewayDispatchService", _FakeDispatchService)

    webhook = SimpleNamespace(id=uuid4(), description="desc", agent_id=None)
    board = SimpleNamespace(id=uuid4(), name="Board")
    payload = SimpleNamespace(id=uuid4(), payload={"event": "test"})

    await dispatch._notify_target_agent(
        session=SimpleNamespace(),
        board=board,
        webhook=webhook,
        payload=payload,
    )

    assert sent == [{"session_key": "lead:session", "agent_name": "Lead Agent"}]


def test_dispatch_run_entrypoint_calls_async_flush(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[bool] = []

    async def _flush() -> None:
        called.append(True)

    monkeypatch.setattr(dispatch, "flush_webhook_delivery_queue", _flush)

    dispatch.run_flush_webhook_delivery_queue()

    assert called == [True]
