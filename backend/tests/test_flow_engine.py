"""Flow engine tests — configurable SOPs, and the hard guarantees:

- the refund flow FILES an approval and escalates; it NEVER auto-executes a refund (Inv 2)
- discounts are capped at 20% no matter what the flow says
- escalate keywords + sticky escalation (Inv 3); untrusted customer text (Inv 4)
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand
from app.models.flow import Flow
from app.models.refunds import RefundRequest
from app.models.tickets import Ticket, TicketMessage
from app.models.vault import VaultDocument
from app.services.agent_runtime.flow import FlowCSRuntime
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.flow_seeds import ensure_seed_flows


class FakeShopify(ShopifyConnector):
    def __init__(self) -> None:
        self.discounts: list[float] = []

    async def get_shop(self) -> dict[str, Any]:
        return {"name": "Chicago Outlet"}

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return {}

    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        return [{"id": 7, "name": "#1001", "total_price": "49.95", "fulfillment_status": "fulfilled"}]

    async def get_fulfillments(self, order_id: str) -> list[dict[str, Any]]:
        return []

    async def list_orders(self, **_k: Any) -> list[dict[str, Any]]:
        return []

    async def create_discount(self, *, title: str, percentage: float, code: str) -> dict[str, Any]:
        self.discounts.append(percentage)
        return {"discount_code": {"code": code}}


class FakeInbox(InboxConnector):
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def health(self) -> dict[str, Any]:
        return {"status": "ACTIVE"}

    async def list_messages(self, *, unread_only: bool = True, limit: int = 25) -> list[dict[str, Any]]:
        return []

    async def send_message(self, *, to: str, subject: str, body: str, in_reply_to: str | None = None) -> dict[str, Any]:
        self.sent.append({"body": body})
        return {"ok": True}


async def _setup() -> tuple[AsyncSession, Brand, FakeShopify, FakeInbox]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="Test")
    session.add(brand)
    await session.flush()
    session.add(
        VaultDocument(
            brand_id=brand.id, slug="shipping-policy", title="Shipping Policy", tags="policy",
            body="Delivery 5-8 days. Track at https://x.myshopify.com/account",
        )
    )
    await ensure_seed_flows(session, brand)
    await session.commit()
    return session, brand, FakeShopify(), FakeInbox()


async def _ticket(session: AsyncSession, brand: Brand, *, subject: str, body: str, status: str = "new") -> Ticket:
    t = Ticket(brand_id=brand.id, subject=subject, customer_email="shopper@example.com",
               customer_name="Pat", status=status, inbound_message_external_id="m1")
    session.add(t)
    await session.flush()
    session.add(TicketMessage(ticket_id=t.id, direction="inbound", author="shopper@example.com", body=body, untrusted=True))
    await session.commit()
    await session.refresh(t)
    return t


async def _reply(session: AsyncSession, ticket: Ticket, body: str) -> None:
    """Simulate a threaded customer reply that re-activates the ticket."""
    session.add(TicketMessage(ticket_id=ticket.id, direction="inbound", author="shopper@example.com", body=body, untrusted=True))
    ticket.status = "auto_handling"
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)


@pytest.mark.asyncio
async def test_seed_flows_present() -> None:
    session, *_ = await _setup()
    flows = (await session.exec(select(Flow))).all()
    intents = {f.intent for f in flows}
    assert {"wismo", "refund"} <= intents


@pytest.mark.asyncio
async def test_wismo_flow_resolves_with_reply_and_evidence() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Where is my order #1001?", body="haven't received #1001")
    res = await rt.handle_ticket(session, t)
    assert res.action == "auto_resolved"
    assert t.status == "resolved"
    assert any("#1001" in s["body"] and "/account" in s["body"] for s in inbox.sent)


@pytest.mark.asyncio
async def test_refund_flow_offers_then_files_approval_never_executes() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="I want a refund for #1001")

    # Turn 1: offer 10%, wait.
    r1 = await rt.handle_ticket(session, t)
    assert r1.action == "awaiting" and t.status == "awaiting_customer"
    assert 10 in shop.discounts

    # Turn 2: customer declines -> offer 20%, wait.
    await _reply(session, t, "No, I still want my money back")
    r2 = await rt.handle_ticket(session, t)
    assert r2.action == "awaiting" and t.status == "awaiting_customer"
    assert 20 in shop.discounts

    # Turn 3: declines again -> file refund approval + escalate to a rep.
    await _reply(session, t, "No refund please")
    r3 = await rt.handle_ticket(session, t)
    assert r3.action == "escalated" and t.status == "needs_rep"

    refunds = (await session.exec(select(RefundRequest))).all()
    assert len(refunds) == 1
    # Filed for approval, NOT executed (Invariant 2).
    assert refunds[0].status == "pending"
    assert not any(r.status == "executed" for r in refunds)


@pytest.mark.asyncio
async def test_refund_flow_accepts_offer_and_resolves() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund for #1001 please")
    await rt.handle_ticket(session, t)  # offer 10%, wait
    await _reply(session, t, "ok yes I'll keep it")
    res = await rt.handle_ticket(session, t)
    assert res.action == "auto_resolved" and t.status == "resolved"
    # No refund was ever filed.
    assert (await session.exec(select(RefundRequest))).all() == []


@pytest.mark.asyncio
async def test_discount_is_capped_at_20() -> None:
    session, brand, shop, inbox = await _setup()
    # Edit the refund flow's first offer to an absurd 75%.
    flow = (await session.exec(select(Flow).where(Flow.intent == "refund"))).first()
    assert flow is not None and flow.steps is not None
    steps = list(flow.steps)
    steps[1] = {**steps[1], "percent": 75}
    flow.steps = steps
    session.add(flow)
    await session.commit()

    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund #1001")
    await rt.handle_ticket(session, t)
    assert shop.discounts and max(shop.discounts) <= 20.0


@pytest.mark.asyncio
async def test_escalate_keyword_goes_straight_to_rep() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund #1001 or I'll file a chargeback")
    res = await rt.handle_ticket(session, t)
    assert res.action == "escalated" and t.status == "needs_rep"
    assert (await session.exec(select(RefundRequest))).all() == []


@pytest.mark.asyncio
async def test_needs_rep_is_never_resumed() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund #1001", status="needs_rep")
    res = await rt.handle_ticket(session, t)
    assert res.action == "skipped" and t.status == "needs_rep"
    assert inbox.sent == []
