"""Tests for the Ecom-OS MCP server (the Hermes ``mcp-ecom-os`` integration surface).

Hermetic: no real network, no real Postgres. The Shopify connector factory is
replaced with a fake and the session factory is an in-memory SQLite session.

Asserts the security-critical guarantees:
  - Invariant 2: the exposed tool set is exactly the read + discount tools, and
    contains NO tool whose name matches refund/cancel/delete/void.
  - create_discount rejects/caps percentage > 20.
  - A tool handler returns structured data.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.mcp_server.server import (
    MAX_DISCOUNT_PERCENTAGE,
    TOOL_NAMES,
    TOOLS,
    DiscountTooLargeError,
    build_handlers,
)
from app.models.brand import Brand, Store
from app.models.tickets import Ticket, TicketMessage
from app.models.vault import VaultDocument
from app.services.connectors.base import ShopifyConnector
from app.services.connectors.secrets import ConnectionRef

FORBIDDEN = re.compile(r"refund|cancel|delete|void", re.IGNORECASE)


class FakeShopify(ShopifyConnector):
    def __init__(self, ref: ConnectionRef) -> None:
        self.ref = ref

    async def get_shop(self) -> dict[str, Any]:
        return {"name": "Chicago Outlet", "domain": "shop.example.com", "currency": "USD"}

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return {}

    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        return [{"name": "#1001", "fulfillment_status": "fulfilled"}]

    async def get_fulfillments(self, order_id: str) -> list[dict[str, Any]]:
        return [{"id": 5, "tracking_number": "TRK1", "status": "success"}]

    async def list_orders(self, **_k: Any) -> list[dict[str, Any]]:
        return []

    async def create_discount(self, *, title: str, percentage: float, code: str) -> dict[str, Any]:
        return {"discount_code": {"code": code}}


async def _seed_engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="Test")
    session.add(brand)
    await session.flush()
    session.add(
        Store(
            brand_id=brand.id,
            name="Test Store",
            domain="shop.example.com",
            provider="direct",
            external_id="shop.example.com",
            status="connected",
        )
    )
    session.add(
        VaultDocument(
            brand_id=brand.id,
            slug="shipping-policy",
            title="Shipping Policy",
            tags="policy,shipping,wismo",
            body="Standard delivery 5-8 days. Track at https://example.myshopify.com/account",
        )
    )
    ticket = Ticket(
        brand_id=brand.id,
        subject="Where is my order?",
        customer_email="shopper@example.com",
        customer_name="Pat",
        status="new",
    )
    session.add(ticket)
    await session.flush()
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            direction="inbound",
            author="shopper@example.com",
            body="status?",
            untrusted=True,
        )
    )
    session.add(
        Ticket(
            brand_id=brand.id,
            subject="Closed one",
            customer_email="done@example.com",
            status="resolved",
        )
    )
    await session.commit()
    await session.close()
    return engine


def _handlers(engine: AsyncEngine) -> dict[str, Any]:
    def session_factory() -> AsyncSession:
        return AsyncSession(engine, expire_on_commit=False)

    return build_handlers(session_factory=session_factory, shopify_factory=FakeShopify)


# --- Invariant 2: tool set is the capability boundary ----------------------
def test_tool_set_is_exactly_read_and_discount() -> None:
    assert TOOL_NAMES == {
        "get_shop_info",
        "lookup_order",
        "get_fulfillments",
        "search_vault",
        "list_open_tickets",
        "get_ticket",
        "create_discount",
    }
    # Every registered Tool name is in the audited set (no drift).
    assert {t.name for t in TOOLS} == TOOL_NAMES


def test_no_refund_or_order_write_tool_exists() -> None:
    """Invariant 2 (explicit): no tool name may match refund/cancel/delete/void."""
    for name in TOOL_NAMES:
        assert not FORBIDDEN.search(name), f"forbidden tool exposed: {name}"
    # And the handler map agrees with the tool list.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    def sf() -> AsyncSession:
        return AsyncSession(engine, expire_on_commit=False)

    handlers = build_handlers(session_factory=sf, shopify_factory=FakeShopify)
    assert set(handlers) == TOOL_NAMES
    for name in handlers:
        assert not FORBIDDEN.search(name)


# --- create_discount caps the only write -----------------------------------
@pytest.mark.asyncio
async def test_create_discount_rejects_above_cap() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    with pytest.raises(DiscountTooLargeError):
        await handlers["create_discount"](
            {"title": "VIP", "percentage": MAX_DISCOUNT_PERCENTAGE + 5, "code": "VIP25"}
        )


@pytest.mark.asyncio
async def test_create_discount_allows_at_or_below_cap() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    out = await handlers["create_discount"](
        {"title": "Sorry", "percentage": MAX_DISCOUNT_PERCENTAGE, "code": "SORRY20"}
    )
    assert out["percentage"] == MAX_DISCOUNT_PERCENTAGE
    assert out["code"] == "SORRY20"
    assert out["result"]["discount_code"]["code"] == "SORRY20"


# --- handlers return structured data (no network) --------------------------
@pytest.mark.asyncio
async def test_get_shop_info_returns_structured_data() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    out = await handlers["get_shop_info"]({})
    assert out["name"] == "Chicago Outlet"
    assert out["currency"] == "USD"


@pytest.mark.asyncio
async def test_lookup_order_returns_structured_data() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    out = await handlers["lookup_order"]({"order_ref": "#1001"})
    assert out["count"] == 1
    assert out["orders"][0]["name"] == "#1001"


@pytest.mark.asyncio
async def test_search_vault_returns_title_excerpt_slug() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    out = await handlers["search_vault"]({"query": "shipping"})
    assert out["results"]
    hit = out["results"][0]
    assert set(hit) == {"title", "slug", "excerpt"}
    assert hit["slug"] == "shipping-policy"


@pytest.mark.asyncio
async def test_list_open_tickets_excludes_resolved() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    out = await handlers["list_open_tickets"]({})
    statuses = {t["status"] for t in out["tickets"]}
    assert "resolved" not in statuses
    assert out["count"] == 1


@pytest.mark.asyncio
async def test_get_ticket_returns_messages() -> None:
    engine = await _seed_engine()
    handlers = _handlers(engine)
    listed = await handlers["list_open_tickets"]({})
    ticket_id = listed["tickets"][0]["id"]
    out = await handlers["get_ticket"]({"ticket_id": ticket_id})
    assert out["found"] is True
    assert out["messages"][0]["direction"] == "inbound"
    assert out["messages"][0]["untrusted"] is True
