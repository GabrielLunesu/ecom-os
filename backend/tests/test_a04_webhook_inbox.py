# ruff: noqa
"""A04 — raw-body signature verification + durable inbox dedup-once."""

from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from app.connectors.durable import InboundEvent, LocalDurableInbox
from app.connectors.errors import WebhookVerificationError
from app.connectors.models import CommerceProviderEvent
from app.connectors.webhooks import WebhookContext, accept_webhook, verify_signature
from sqlmodel import func, select
from tests.a04_helpers import open_session

SECRET = "whsec_test"


def _hex_sig(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _b64_sig(body: bytes) -> str:
    return base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()


def test_verify_hex_and_base64() -> None:
    body = b'{"id":1,"topic":"orders/create"}'
    assert verify_signature(SECRET, body, _hex_sig(body), scheme="hex")
    assert verify_signature(SECRET, body, _b64_sig(body), scheme="base64")


def test_verify_rejects_tampered_body_and_wrong_secret() -> None:
    body = b'{"id":1}'
    assert not verify_signature(SECRET, body + b" ", _hex_sig(body), scheme="hex")
    assert not verify_signature("other", body, _hex_sig(body), scheme="hex")
    assert not verify_signature(SECRET, body, None, scheme="hex")


def _ctx(event_id: str = "evt-1", topic: str = "orders/create") -> WebhookContext:
    return WebhookContext(
        source="shopify",
        account_ref="shop.myshopify.com",
        source_event_id=event_id,
        topic=topic,
        secret=SECRET,
        scheme="base64",
    )


async def _count_events(session) -> int:
    res = await session.exec(select(func.count()).select_from(CommerceProviderEvent))
    return int(res.one())


@pytest.mark.asyncio
async def test_invalid_signature_never_persisted() -> None:
    async with open_session() as session:
        inbox = LocalDurableInbox(session)
        body = b'{"id":1}'
        with pytest.raises(WebhookVerificationError):
            await accept_webhook(inbox, _ctx(), body, "sha256=deadbeef")
        await session.commit()
        assert await _count_events(session) == 0


@pytest.mark.asyncio
async def test_missing_event_id_rejected() -> None:
    async with open_session() as session:
        inbox = LocalDurableInbox(session)
        body = b'{"id":1}'
        with pytest.raises(WebhookVerificationError):
            await accept_webhook(inbox, _ctx(event_id=""), body, _b64_sig(body))


@pytest.mark.asyncio
async def test_duplicate_webhook_accepted_once() -> None:
    async with open_session() as session:
        inbox = LocalDurableInbox(session)
        body = b'{"id":1,"topic":"orders/create"}'
        sig = _b64_sig(body)

        ev1, dup1 = await accept_webhook(inbox, _ctx(), body, sig)
        assert dup1 is False
        ev2, dup2 = await accept_webhook(inbox, _ctx(), body, sig)
        assert dup2 is True
        assert ev2.id == ev1.id
        await session.commit()
        # Exactly one durable row despite two deliveries (I-07).
        assert await _count_events(session) == 1


@pytest.mark.asyncio
async def test_inbox_dedup_direct_insert() -> None:
    async with open_session() as session:
        inbox = LocalDurableInbox(session)
        evt = InboundEvent(
            source="inbox",
            source_event_id="m-1",
            account_ref="ca_123",
            topic="message",
            payload_hash="sha256:x",
            verification="verified",
            occurred_at=None,
        )
        _, d1 = await inbox.accept(evt)
        _, d2 = await inbox.accept(evt)
        assert (d1, d2) == (False, True)
        await session.commit()
        assert await _count_events(session) == 1
