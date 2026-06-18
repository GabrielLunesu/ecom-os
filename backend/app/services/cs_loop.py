"""CS loop: ingest mail, then run the AgentRuntime over actionable tickets.

Refuses to run until Shopify + the inbox are live (Build Spec §1.5). Builds the
runtime with a read+discount Shopify connector and the inbox connector — never a
refund tool (Invariant 2).
"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.models.brand import Store
from app.models.tickets import Ticket
from app.services.agent_runtime.base import AgentRuntime
from app.services.agent_runtime.flow import FlowCSRuntime
from app.services.agent_runtime.hermes import HermesRuntime
from app.services.agent_runtime.in_app import InAppCSRuntime
from app.services.agent_runtime.llm import LLMCSRuntime
from app.services.connection_health import assert_ready_for_cs_loop
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.connectors.composio_inbox import (
    ComposioInboxConnector,
    discover_active_mail_account,
)
from app.services.connectors.registry import shopify_connector_for
from app.services.connectors.secrets import ConnectionRef, env_or_setting
from app.services.flow_seeds import ensure_seed_flows
from app.services.stores import ensure_seed, list_stores
from app.services.tickets import ingest_inbox

logger = get_logger(__name__)
# Only these lanes are eligible for autonomous handling (Invariant 3).
_ACTIONABLE = ("new", "auto_handling")


def _select_runtime(shopify: ShopifyConnector, inbox: InboxConnector, store: Store) -> AgentRuntime:
    """Pick the CS brain from CS_RUNTIME: "" deterministic | "flow" | "llm" | "hermes".

    All take read + discount tools only — never a refund tool (Invariant 2). The flow
    runtime also gets the operator-set store profile (public URL, signature) so it
    never hallucinates store facts.
    """
    mode = env_or_setting("CS_RUNTIME").lower()
    if mode == "hermes":
        return HermesRuntime(shopify=shopify, inbox=inbox, store_domain=store.domain)
    if mode == "llm":
        return LLMCSRuntime(shopify=shopify, inbox=inbox, store_domain=store.domain)
    if mode == "flow":
        return FlowCSRuntime(
            shopify=shopify,
            inbox=inbox,
            store_domain=store.domain,
            public_url=store.public_url,
            support_name=store.support_name or "Support",
            tracking_url=store.tracking_url,
            facts=store.facts,
        )
    return InAppCSRuntime(shopify=shopify, inbox=inbox, store_domain=store.domain)


async def run_cs_loop(session: AsyncSession) -> dict[str, object]:
    brand = await ensure_seed(session)
    await assert_ready_for_cs_loop(session)  # gate (§1.5)
    await ensure_seed_flows(session, brand)  # default WISMO + refund flows
    stores = await list_stores(session)
    if not stores:
        return {"error": "no store connected"}
    store = stores[0]

    # 1. Ingest new mail.
    created = await ingest_inbox(session, brand)

    # 2. Build the runtime (read + discounts; no refund tool — Invariant 2).
    shopify = shopify_connector_for(
        ConnectionRef(provider=store.provider, external_id=store.external_id)
    )
    account_id = await discover_active_mail_account()
    inbox = ComposioInboxConnector(ConnectionRef(provider="composio", external_id=account_id or ""))
    runtime = _select_runtime(shopify, inbox, store)

    # 3. Handle actionable tickets.
    actionable = (
        await session.exec(select(Ticket).where(Ticket.status.in_(_ACTIONABLE)))  # type: ignore[attr-defined]
    ).all()
    results = []
    for ticket in actionable:
        res = await runtime.handle_ticket(session, ticket)
        results.append(
            {"ticket_id": str(ticket.id), "subject": ticket.subject, "action": res.action}
        )

    return {
        "ingested": len(created),
        "handled": len(results),
        "results": results,
    }
