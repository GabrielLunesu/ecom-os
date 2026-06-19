"""Ingestion tests (Build Spec §7, Invariant 4: untrusted, delimited input)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand
from app.models.tickets import Ticket, TicketMessage
from app.services import tickets as tickets_svc
from app.services.connectors.composio_inbox import normalize_message
from app.services.tickets import (
    _is_support_candidate,
    append_reply,
    create_ticket_from_message,
    ingest_inbox,
    ticket_messages,
)

SAMPLE_GRAPH_MSG = {
    "id": "AAMk-msg-1",
    "conversationId": "conv-1",
    "subject": "Where is my order #1001?",
    "from": {"emailAddress": {"address": "shopper@example.com", "name": "Pat Shopper"}},
    "body": {"contentType": "html", "content": "<p>Hi, where is my order <b>#1001</b>?</p>"},
    "receivedDateTime": "2026-06-17T10:00:00Z",
    "isRead": False,
}


async def _session() -> AsyncSession:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False)


def test_normalize_message_strips_html() -> None:
    norm = normalize_message(SAMPLE_GRAPH_MSG)
    assert norm["from_email"] == "shopper@example.com"
    assert norm["subject"] == "Where is my order #1001?"
    assert "<p>" not in norm["body_text"]
    assert "#1001" in norm["body_text"]


def test_support_candidate_filters_automated() -> None:
    assert _is_support_candidate("shopper@example.com") is True
    assert _is_support_candidate("noreply.notifications@trustpilot.com") is False
    assert _is_support_candidate("no-reply@pinterest.com") is False
    assert _is_support_candidate("") is False


@pytest.mark.asyncio
async def test_inbound_message_is_untrusted() -> None:
    """Invariant 4: ingested customer text is stored untrusted, never instructions."""
    async with await _session() as session:
        brand = Brand(name="Test")
        session.add(brand)
        await session.flush()
        ticket = await create_ticket_from_message(
            session, brand, normalize_message(SAMPLE_GRAPH_MSG)
        )
        assert ticket.status == "new"
        msgs = await ticket_messages(session, ticket.id)
        assert len(msgs) == 1
        assert msgs[0].direction == "inbound"
        assert msgs[0].untrusted is True


@pytest.mark.asyncio
async def test_ingest_dedups_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    async with await _session() as session:
        brand = Brand(name="Test")
        session.add(brand)
        await session.flush()

        noise = dict(SAMPLE_GRAPH_MSG, id="noise-1")
        noise["from"] = {"emailAddress": {"address": "noreply@trustpilot.com", "name": "TP"}}
        normalized = [normalize_message(SAMPLE_GRAPH_MSG), normalize_message(noise)]

        class FakeInbox:
            def __init__(self, *_a, **_k):
                pass

            async def list_messages(self, **_k):
                return normalized

        async def fake_discover(*_a, **_k):
            return "ca_test"

        monkeypatch.setattr(tickets_svc, "discover_active_mail_account", fake_discover)
        monkeypatch.setattr(tickets_svc, "ComposioInboxConnector", FakeInbox)

        first = await ingest_inbox(session, brand)
        assert len(first) == 1  # noise filtered out, one real ticket
        assert first[0].customer_email == "shopper@example.com"

        # Re-running ingests nothing new (dedup by external_id).
        second = await ingest_inbox(session, brand)
        assert second == []

        total = (await session.exec(select(TicketMessage))).all()
        assert len(total) == 1


@pytest.mark.asyncio
async def test_reply_resumes_awaiting_ticket() -> None:
    async with await _session() as session:
        brand = Brand(name="Test")
        session.add(brand)
        await session.flush()
        t = Ticket(
            brand_id=brand.id,
            subject="Refund",
            customer_email="s@x.com",
            status="awaiting_customer",
            external_ref="conv-1",
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        reply = dict(SAMPLE_GRAPH_MSG, id="reply-1", conversationId="conv-1")
        await append_reply(session, t, normalize_message(reply))
        assert t.status == "auto_handling"  # resumed
        assert len(await ticket_messages(session, t.id)) == 1


@pytest.mark.asyncio
async def test_reply_to_needs_rep_stays_sticky() -> None:
    async with await _session() as session:
        brand = Brand(name="Test")
        session.add(brand)
        await session.flush()
        t = Ticket(
            brand_id=brand.id,
            subject="Complaint",
            customer_email="s@x.com",
            status="needs_rep",
            external_ref="conv-2",
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        await append_reply(
            session, t, normalize_message(dict(SAMPLE_GRAPH_MSG, id="r2", conversationId="conv-2"))
        )
        assert t.status == "needs_rep"  # Invariant 3: never re-auto
