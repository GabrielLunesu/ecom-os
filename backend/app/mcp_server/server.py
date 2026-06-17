"""Ecom-OS MCP stdio server — the integration surface for the Hermes CS subagent.

Invariant 2 (HARD, structural): the only tools registered here are READ tools and a
single, percentage-capped ``create_discount``. There is intentionally **no refund,
cancel, void, or any order-write tool** anywhere in this module. The exposed tool
list *is* the capability boundary — a Hermes ``cs`` profile pointed at this server
(``--toolsets "mcp-ecom-os"``) is structurally incapable of issuing a refund.

Invariant 5: tools return order / ticket / vault data only. Secrets are resolved
internally by the connector layer (held as ``Secret``) and never returned or logged.

The server is provider-agnostic: the Shopify connector is built from the seeded
store's ``ConnectionRef`` via ``shopify_connector_for``, and DB-backed tools use the
app's ``async_session_maker``. Both are injected as factories so tests can run the
handlers with no network and no Postgres.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import mcp.types as types
from mcp.server.lowlevel import Server
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.models.brand import Store
from app.services import tickets as tickets_service
from app.services import vault as vault_service
from app.services.connectors import ShopifyConnector, shopify_connector_for
from app.services.connectors.secrets import ConnectionRef

logger = get_logger(__name__)

SERVER_NAME = "mcp-ecom-os"

# Invariant 2: discounts the CS agent may create are capped. Anything above this is
# rejected (not silently inflated above the cap, and never escalated to a refund).
MAX_DISCOUNT_PERCENTAGE = 20.0

# Type aliases for the injectable dependencies (keep handlers hermetic in tests).
SessionFactory = Callable[[], AsyncSession]
ShopifyFactory = Callable[[ConnectionRef], ShopifyConnector]


class DiscountTooLargeError(ValueError):
    """Raised when a requested discount exceeds the CS agent's hard cap."""


# --- tool schema (the capability boundary) ---------------------------------
# NOTE: keep this list audited. Adding a refund/cancel/void/delete tool here would
# violate Invariant 2. The test suite asserts no such name can appear.
TOOLS: list[types.Tool] = [
    types.Tool(
        name="get_shop_info",
        description="Read basic info about the connected Shopify store.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    types.Tool(
        name="lookup_order",
        description="Find orders by order name (e.g. '#1001') or customer email.",
        inputSchema={
            "type": "object",
            "properties": {"order_ref": {"type": "string"}},
            "required": ["order_ref"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="get_fulfillments",
        description="Read tracking / shipping fulfillments for an order id (WISMO).",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="search_vault",
        description="Search the brand vault (policies/SOPs); returns title, excerpt, slug.",
        inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="list_open_tickets",
        description="List CS tickets that are not yet resolved.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    types.Tool(
        name="get_ticket",
        description="Read a single ticket with its full message history.",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="create_discount",
        description=(
            "Create a percentage discount code. Percentage is hard-capped at "
            f"{int(MAX_DISCOUNT_PERCENTAGE)}%. The ONLY write the CS agent may do — "
            "there is no refund/cancel tool."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "percentage": {"type": "number"},
                "code": {"type": "string"},
            },
            "required": ["title", "percentage", "code"],
            "additionalProperties": False,
        },
    ),
]

# Exact, audited set of tool names this server is allowed to expose (Invariant 2).
TOOL_NAMES: frozenset[str] = frozenset(t.name for t in TOOLS)


async def _resolve_store_ref(session: AsyncSession) -> ConnectionRef:
    """Build the ConnectionRef for the seeded store (refs only — Invariant 1)."""
    store = (await session.exec(select(Store).order_by(Store.name))).first()
    if store is None:
        raise RuntimeError("no store connected; connect a store in Settings first")
    return ConnectionRef(provider=store.provider, external_id=store.external_id)


def build_handlers(
    *,
    session_factory: SessionFactory,
    shopify_factory: ShopifyFactory = shopify_connector_for,
) -> dict[str, Callable[[dict[str, Any]], Awaitable[Any]]]:
    """Build the tool-name -> async handler map.

    Dependencies are injected so tests can monkeypatch the connector factory and the
    session, keeping handlers hermetic (no real network, no real Postgres).
    """

    async def _shopify(session: AsyncSession) -> ShopifyConnector:
        ref = await _resolve_store_ref(session)
        return shopify_factory(ref)

    async def get_shop_info(_args: dict[str, Any]) -> dict[str, Any]:
        async with session_factory() as session:
            shop = await (await _shopify(session)).get_shop()
        return {
            "name": shop.get("name"),
            "domain": shop.get("domain") or shop.get("myshopify_domain"),
            "currency": shop.get("currency"),
            "email": shop.get("email"),
        }

    async def lookup_order(args: dict[str, Any]) -> dict[str, Any]:
        order_ref = str(args["order_ref"]).strip()
        async with session_factory() as session:
            orders = await (await _shopify(session)).search_orders(order_ref)
        return {"order_ref": order_ref, "count": len(orders), "orders": orders}

    async def get_fulfillments(args: dict[str, Any]) -> dict[str, Any]:
        order_id = str(args["order_id"]).strip()
        async with session_factory() as session:
            fulfillments = await (await _shopify(session)).get_fulfillments(order_id)
        return {"order_id": order_id, "fulfillments": fulfillments}

    async def search_vault(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args["query"]).strip()
        async with session_factory() as session:
            docs = await vault_service.search(session, query)
            results = [
                {
                    "title": doc.title,
                    "slug": doc.slug,
                    "excerpt": doc.body[:280].strip(),
                }
                for doc in docs
            ]
        return {"query": query, "results": results}

    async def list_open_tickets(_args: dict[str, Any]) -> dict[str, Any]:
        async with session_factory() as session:
            all_tickets = await tickets_service.list_tickets(session)
            open_tickets = [
                {
                    "id": str(t.id),
                    "subject": t.subject,
                    "status": t.status,
                    "customer_email": t.customer_email,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in all_tickets
                if t.status != "resolved"
            ]
        return {"count": len(open_tickets), "tickets": open_tickets}

    async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
        ticket_id = UUID(str(args["ticket_id"]))
        async with session_factory() as session:
            ticket = await tickets_service.get_ticket(session, ticket_id)
            if ticket is None:
                return {"ticket_id": str(ticket_id), "found": False}
            messages = await tickets_service.ticket_messages(session, ticket_id)
            payload = {
                "ticket_id": str(ticket.id),
                "found": True,
                "subject": ticket.subject,
                "status": ticket.status,
                "customer_email": ticket.customer_email,
                "customer_name": ticket.customer_name,
                "messages": [
                    {
                        "direction": m.direction,
                        "author": m.author,
                        "body": m.body,
                        "untrusted": m.untrusted,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ],
            }
        return payload

    async def create_discount(args: dict[str, Any]) -> dict[str, Any]:
        title = str(args["title"]).strip()
        code = str(args["code"]).strip()
        percentage = float(args["percentage"])
        # Invariant 2: cap the only write the CS agent can do. Reject, never inflate.
        if percentage > MAX_DISCOUNT_PERCENTAGE:
            raise DiscountTooLargeError(
                f"discount {percentage}% exceeds the {MAX_DISCOUNT_PERCENTAGE}% cap",
            )
        async with session_factory() as session:
            shopify = await _shopify(session)
        result = await shopify.create_discount(title=title, percentage=percentage, code=code)
        return {"title": title, "code": code, "percentage": percentage, "result": result}

    return {
        "get_shop_info": get_shop_info,
        "lookup_order": lookup_order,
        "get_fulfillments": get_fulfillments,
        "search_vault": search_vault,
        "list_open_tickets": list_open_tickets,
        "get_ticket": get_ticket,
        "create_discount": create_discount,
    }


def build_server(
    *,
    session_factory: SessionFactory | None = None,
    shopify_factory: ShopifyFactory = shopify_connector_for,
) -> Server:
    """Construct the low-level MCP server with read + discount tools registered.

    ``session_factory`` defaults to the app's ``async_session_maker`` (imported
    lazily so the module imports without a configured database).
    """
    if session_factory is None:
        from app.db.session import async_session_maker

        session_factory = async_session_maker

    handlers = build_handlers(session_factory=session_factory, shopify_factory=shopify_factory)
    server: Server = Server(SERVER_NAME)

    @server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def _list_tools() -> list[types.Tool]:
        return TOOLS

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"unknown tool: {name!r}")
        logger.info("mcp.tool.call", extra={"tool": name})
        result: Any = await handler(arguments or {})
        return {"result": result}

    return server


async def run_stdio() -> None:
    """Run the MCP server over stdio (the Hermes ``mcp-ecom-os`` launch entrypoint)."""
    from mcp.server.stdio import stdio_server

    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
