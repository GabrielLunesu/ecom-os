"""Realtime inbound-email webhook: secret-gated, schedules the loop, fast 200."""

from __future__ import annotations

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request

from app.api.ecom_webhooks import email_webhook, webhook_secret


def _req(method: str, query_string: bytes = b"") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/ecom/webhooks/email",
            "query_string": query_string,
            "headers": [],
            "scheme": "http",
            "server": ("test", 80),
        }
    )


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
async def test_post_with_secret_schedules_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECOM_WEBHOOK_SECRET", "s3cr3t")
    bg = BackgroundTasks()
    resp = await email_webhook(_req("POST", b"token=s3cr3t"), bg)
    assert resp.status_code == 202
    assert len(bg.tasks) == 1  # CS loop scheduled in the background


def test_secret_derives_from_local_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.delenv("ECOM_WEBHOOK_SECRET", raising=False)
    monkeypatch.setattr(settings, "ecom_webhook_secret", "")
    monkeypatch.setenv("LOCAL_AUTH_TOKEN", "x" * 60)
    s = webhook_secret()
    assert s and len(s) == 32
