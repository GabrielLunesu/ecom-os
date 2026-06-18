"""Flow engine tests — the LLM-driven branching graph, and the hard guarantees:

- every customer email is generated via cs_llm (here a fake; NO network is hit)
- the refund flow FILES an approval and escalates; it NEVER auto-executes a refund (Inv 2)
- branching: a "not satisfied" reply advances down the funnel; "satisfied" resolves
- classify fallback (-1) takes the safe (last) branch
- discounts are created from step CONFIG and capped no matter what the flow says
- escalate keywords + sticky escalation (Inv 3); untrusted customer text (Inv 4)
- the deterministic template fallback (no prompt / no LLM) still works
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
from app.services import cs_llm
from app.services.agent_runtime.flow import FlowCSRuntime
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.flow_seeds import ensure_seed_flows

_DECLINE = ("no", "not", "still want", "refund please", "money back", "decline")


def _fake_messages_factory() -> Any:
    """Build a fake cs_llm._messages that returns deterministic content (no network).

    - Email calls (system mentions 'write exactly ONE') echo the grounded CONTEXT so
      tests can assert on order name / tracking / discount code in the body.
    - Classify calls (system mentions 'classify') return index 1 ('not satisfied') when
      the customer reply looks like a decline, else 0 ('satisfied').
    """

    async def _fake(payload: dict[str, Any]) -> dict[str, Any]:
        system = payload.get("system", "")
        user = payload["messages"][0]["content"]
        if "classify" in system.lower():
            lower = user.lower()
            # Find the delimited customer reply.
            start = lower.find("<customer_message>")
            reply = lower[start:] if start >= 0 else lower
            idx = 1 if any(w in reply for w in _DECLINE) else 0
            return {"content": [{"type": "text", "text": str(idx)}]}
        # Email generation: surface the CONTEXT block verbatim so assertions can match.
        ctx_start = user.find("CONTEXT")
        ctx = user[ctx_start:] if ctx_start >= 0 else user
        return {"content": [{"type": "text", "text": f"Dear customer,\n\n{ctx}\n\nBest"}]}

    return _fake


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch the single HTTP boundary + a present API key (no network, no secret)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(cs_llm, "_messages", _fake_messages_factory())


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
async def test_wismo_flow_waits_then_resolves_when_customer_is_satisfied() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Where is my order #1001?", body="haven't received #1001")
    first = await rt.handle_ticket(session, t)
    assert first.action == "awaiting"
    assert t.status == "awaiting_customer"
    # The LLM email is grounded in real order context (name + tracking link) and waits.
    assert any("#1001" in s["body"] and "/account" in s["body"] for s in inbox.sent)

    await _reply(session, t, "yes I found it, thank you")
    res = await rt.handle_ticket(session, t)
    assert res.action == "auto_resolved"
    assert t.status == "resolved"


@pytest.mark.asyncio
async def test_wismo_flow_escalates_when_customer_still_has_not_received_order() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Where is my order #1001?", body="where is order #1001?")
    first = await rt.handle_ticket(session, t)
    assert first.action == "awaiting"
    assert t.status == "awaiting_customer"

    await _reply(session, t, "No, I haven't received anything")
    res = await rt.handle_ticket(session, t)
    assert res.action == "escalated"
    assert t.status == "needs_rep"
    assert len(inbox.sent) == 2


@pytest.mark.asyncio
async def test_refund_flow_branches_then_files_approval_never_executes() -> None:
    session, brand, shop, inbox = await _setup()
    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="I want a refund for #1001")

    # Turn 1: offer_50 -> discount from CONFIG (50%), wait.
    r1 = await rt.handle_ticket(session, t)
    assert r1.action == "awaiting" and t.status == "awaiting_customer"
    assert 50.0 in shop.discounts  # the merchant-configured 50% coupon was created

    # Turn 2: "not satisfied" reply -> branch to offer_80, wait.
    await _reply(session, t, "No, I still want my money back")
    r2 = await rt.handle_ticket(session, t)
    assert r2.action == "awaiting" and t.status == "awaiting_customer"
    assert len(shop.discounts) == 2  # second offer's code

    # Turn 3: declines again -> file_refund -> file approval + escalate to a rep.
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
    await rt.handle_ticket(session, t)  # offer_50, wait
    await _reply(session, t, "ok yes that works, I'll keep it")
    res = await rt.handle_ticket(session, t)
    assert res.action == "auto_resolved" and t.status == "resolved"
    # No refund was ever filed.
    assert (await session.exec(select(RefundRequest))).all() == []


@pytest.mark.asyncio
async def test_classify_fallback_takes_safe_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """classify_reply returning -1 must take the LAST (safest) branch."""
    session, brand, shop, inbox = await _setup()

    async def _always_fail(*, branches: list[str], reply: str, context: dict[str, Any]) -> int:
        return -1

    monkeypatch.setattr(cs_llm, "classify_reply", _always_fail)

    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund #1001 please")
    await rt.handle_ticket(session, t)  # offer_50, wait
    # Even an "accept"-looking reply must take the safe branch (offer_80) on failure.
    await _reply(session, t, "yes sounds great")
    res = await rt.handle_ticket(session, t)
    assert res.action == "awaiting" and t.status == "awaiting_customer"
    assert len(shop.discounts) == 2  # advanced to offer_80, not resolved


@pytest.mark.asyncio
async def test_discount_created_from_step_config_and_capped() -> None:
    session, brand, shop, inbox = await _setup()
    # The merchant sets the tier per step (e.g. 80% coupons are valid). A config typo
    # above the 100% ceiling is clamped — the value never comes from the customer/LLM.
    flow = (await session.exec(select(Flow).where(Flow.intent == "refund"))).first()
    assert flow is not None and flow.steps is not None
    steps = list(flow.steps)
    steps[0] = {**steps[0], "discount_percent": 150}
    flow.steps = steps
    session.add(flow)
    await session.commit()

    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Refund", body="refund #1001")
    await rt.handle_ticket(session, t)
    assert shop.discounts and max(shop.discounts) == 100.0  # clamped to the ceiling


@pytest.mark.asyncio
async def test_generation_failure_never_leaks_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the LLM is unavailable, the internal step prompt must NEVER be emailed."""
    session, brand, shop, inbox = await _setup()

    async def _boom(**_kwargs: Any) -> str:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    monkeypatch.setattr(cs_llm, "generate_email", _boom)

    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Where is my order #1001?", body="where is #1001")
    await rt.handle_ticket(session, t)

    flow = (await session.exec(select(Flow).where(Flow.intent == "wismo"))).first()
    assert flow is not None and flow.steps
    prompt = str(flow.steps[0].get("prompt", ""))
    assert prompt and inbox.sent
    body = inbox.sent[-1]["body"]
    assert prompt not in body  # the internal instruction is never sent to the customer
    assert "#1001" in body
    assert "fulfilled" in body
    assert "/account" in body


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


@pytest.mark.asyncio
async def test_deterministic_template_fallback_when_step_has_no_prompt() -> None:
    """A message-free legacy step (send_reply with `message`, no prompt) still renders."""
    session, brand, shop, inbox = await _setup()
    flow = (await session.exec(select(Flow).where(Flow.intent == "wismo"))).first()
    assert flow is not None
    flow.steps = [
        {"type": "lookup_order"},
        {"type": "send_reply", "message": "Hi {customer_name}, your order is {order_name}."},
        {"type": "resolve"},
    ]
    session.add(flow)
    await session.commit()

    rt = FlowCSRuntime(shopify=shop, inbox=inbox, store_domain="x.myshopify.com")
    t = await _ticket(session, brand, subject="Where is my order #1001?", body="status of #1001")
    res = await rt.handle_ticket(session, t)
    assert res.action == "auto_resolved"
    # Rendered from the template (not the LLM echo format), grounded in the order name.
    assert any(s["body"] == "Hi Pat, your order is #1001." for s in inbox.sent)
