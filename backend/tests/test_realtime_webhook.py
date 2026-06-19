"""Realtime inbound-email webhook: secret-gated, schedules the loop, fast 200."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.requests import Request

import app.models  # noqa: F401 - ensure all SQLModel tables are registered
from app.api import ecom_webhooks
from app.api.ecom_webhooks import (
    email_webhook,
    persist_realtime_email_trigger,
    webhook_secret,
)
from app.models.events import DurableInboxEvent, DurableJob


def _req(
    method: str,
    query_string: bytes = b"",
    *,
    body: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    sent = False

    async def _receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/ecom/webhooks/email",
            "query_string": query_string,
            "headers": headers or [],
            "scheme": "http",
            "server": ("test", 80),
        },
        _receive,
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


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_get_ping_is_ok_no_action() -> None:
    bg = BackgroundTasks()
    resp = await email_webhook(_req("GET"), bg)
    assert resp.status_code == 200
    assert len(bg.tasks) == 0


@pytest.mark.asyncio
async def test_post_rejects_bad_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECOM_WEBHOOK_SECRET", "s3cr3t")
    bg = BackgroundTasks()
    resp = await email_webhook(_req("POST", b"token=wrong"), bg)
    assert resp.status_code == 401
    assert len(bg.tasks) == 0  # loop NOT scheduled


@pytest.mark.asyncio
async def test_post_with_secret_persists_durable_trigger_then_schedules_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECOM_WEBHOOK_SECRET", "s3cr3t")
    fake_session = _FakeSession()
    calls: list[str] = []

    async def _persist(session: object, *, request: Request, raw_body: bytes) -> object:
        assert session is fake_session
        assert request.method == "POST"
        assert raw_body == b'{"event":"message"}'
        calls.append("persist")
        return SimpleNamespace(job_created=True)

    monkeypatch.setattr(
        ecom_webhooks, "async_session_maker", lambda: _FakeSessionContext(fake_session)
    )
    monkeypatch.setattr(ecom_webhooks, "persist_realtime_email_trigger", _persist)
    bg = BackgroundTasks()
    resp = await email_webhook(
        _req("POST", b"token=s3cr3t", body=b'{"event":"message"}'),
        bg,
    )
    assert resp.status_code == 202
    assert calls == ["persist"]
    assert fake_session.committed is True
    assert len(bg.tasks) == 1  # CS loop scheduled in the background for a new durable job


@pytest.mark.asyncio
async def test_duplicate_durable_trigger_does_not_reschedule_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECOM_WEBHOOK_SECRET", "s3cr3t")
    fake_session = _FakeSession()

    async def _persist(session: object, *, request: Request, raw_body: bytes) -> object:
        del session, request, raw_body
        return SimpleNamespace(job_created=False)

    monkeypatch.setattr(
        ecom_webhooks, "async_session_maker", lambda: _FakeSessionContext(fake_session)
    )
    monkeypatch.setattr(ecom_webhooks, "persist_realtime_email_trigger", _persist)
    bg = BackgroundTasks()
    resp = await email_webhook(_req("POST", b"token=s3cr3t"), bg)
    assert resp.status_code == 202
    assert fake_session.committed is True
    assert len(bg.tasks) == 0


@pytest.mark.asyncio
async def test_post_returns_retryable_failure_when_durable_acceptance_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECOM_WEBHOOK_SECRET", "s3cr3t")
    fake_session = _FakeSession()

    async def _persist(session: object, *, request: Request, raw_body: bytes) -> object:
        del session, request, raw_body
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        ecom_webhooks, "async_session_maker", lambda: _FakeSessionContext(fake_session)
    )
    monkeypatch.setattr(ecom_webhooks, "persist_realtime_email_trigger", _persist)
    bg = BackgroundTasks()
    resp = await email_webhook(_req("POST", b"token=s3cr3t"), bg)
    assert resp.status_code == 503
    assert fake_session.committed is False
    assert fake_session.rolled_back is True
    assert len(bg.tasks) == 0


@pytest.mark.asyncio
async def test_persist_realtime_email_trigger_deduplicates_event_and_job() -> None:
    async with _session() as session:
        request = _req(
            "POST",
            body=b'{"messageId":"m-1"}',
            headers=[
                (b"x-composio-event-id", b"evt-1"),
                (b"content-type", b"application/json"),
            ],
        )
        first = await persist_realtime_email_trigger(
            session,
            request=request,
            raw_body=b'{"messageId":"m-1"}',
        )
        second = await persist_realtime_email_trigger(
            session,
            request=request,
            raw_body=b'{"messageId":"m-1"}',
        )

        events = list((await session.exec(select(DurableInboxEvent))).all())
        jobs = list((await session.exec(select(DurableJob))).all())

        assert first.event_created is True
        assert first.job_created is True
        assert second.event_created is False
        assert second.job_created is False
        assert second.event_id == first.event_id
        assert second.job_id == first.job_id
        assert len(events) == 1
        assert events[0].source_event_id == "evt-1"
        assert events[0].data == {"messageId": "m-1"}
        assert len(jobs) == 1
        assert jobs[0].job_type == "cs.realtime_email.received"


def test_secret_derives_from_local_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.delenv("ECOM_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(settings, "ecom_webhook_secret", "")
    monkeypatch.setenv("LOCAL_AUTH_TOKEN", "x" * 60)
    s = webhook_secret()
    assert s and len(s) == 32
