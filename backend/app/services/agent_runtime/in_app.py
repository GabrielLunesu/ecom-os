"""In-app CS runtime (v1): deterministic WISMO SOP behind the AgentRuntime interface.

Flow for a `new`/`auto_handling` ticket:
  1. Sticky escalation guard (Invariant 3): never touch needs_rep/resolved tickets.
  2. Classify WISMO from the (untrusted) text; non-WISMO -> escalate to a rep.
  3. Look up the order in Shopify (read-only), cite the vault shipping policy, and
     point the customer at the tracking page — recording evidence for each step.
  4. Send the reply via the inbox and auto-close the ticket (resolved).

The runtime holds a `ShopifyConnector` (read + discounts) and the inbox connector.
It has NO refund tool (Invariant 2): refunds go through the separate RefundExecutor.
"""

from __future__ import annotations

import re
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.core.time import utcnow
from app.models.tickets import Ticket, TicketAudit, TicketEvidence, TicketMessage
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.tickets import ticket_messages
from app.services.vault import get_document

from .base import AgentRuntime, HandlingResult
from .wismo import compose_wismo_reply, extract_order_ref, is_wismo

logger = get_logger(__name__)
_URL_RE = re.compile(r"https?://[^\s)]+")
# Statuses the loop will never auto-handle (Invariant 3: sticky escalation).
_FROZEN = ("needs_rep", "resolved")


class InAppCSRuntime(AgentRuntime):
    def __init__(self, shopify: ShopifyConnector, inbox: InboxConnector, store_domain: str):
        self.shopify = shopify
        self.inbox = inbox
        self.store_domain = store_domain

    async def handle_ticket(self, session: AsyncSession, ticket: Ticket) -> HandlingResult:
        # 1. Sticky escalation: a rep owns this; never re-auto (Invariant 3).
        if ticket.status in _FROZEN:
            return HandlingResult("skipped", ticket.status, False, "frozen (sticky escalation)")

        msgs = await ticket_messages(session, ticket.id)
        inbound = next((m for m in msgs if m.direction == "inbound"), None)
        body = inbound.body if inbound else ""

        # 2. Classify. Non-WISMO -> escalate to a human rep.
        if not is_wismo(ticket.subject, body):
            return await self._escalate(session, ticket, "non-WISMO intent; needs a rep")

        ticket.status = "auto_handling"
        ticket.updated_at = utcnow()
        session.add(ticket)
        await session.commit()

        # 3a. Order lookup (read-only).
        order_ref = extract_order_ref(f"{ticket.subject}\n{body}")
        order = await self._lookup_order(order_ref)
        await self._evidence(
            session,
            ticket,
            "order_lookup",
            f"order {order.get('name') if order else order_ref or 'unknown'}",
            {
                "order_ref": order_ref,
                "found": bool(order),
                "fulfillment_status": (order or {}).get("fulfillment_status"),
            },
        )

        # 3b. Cite the shipping policy from the vault + resolve the tracking page.
        shipping = await get_document(session, "shipping-policy")
        policy_text = shipping.body if shipping else ""
        excerpt = _policy_excerpt(policy_text)
        tracking_url = _tracking_url(policy_text, self.store_domain)
        await self._evidence(
            session, ticket, "policy_cite", "shipping-policy", {"slug": "shipping-policy"}
        )
        await self._evidence(session, ticket, "tracking", tracking_url, {"url": tracking_url})

        # 3c. Compose + 4. send the reply, then auto-close.
        reply = compose_wismo_reply(
            order=order,
            order_ref=order_ref,
            shipping_policy_excerpt=excerpt,
            tracking_url=tracking_url,
            customer_name=ticket.customer_name,
        )
        await self.inbox.send_message(
            to=ticket.customer_email,
            subject=f"Re: {ticket.subject}",
            body=reply,
            in_reply_to=ticket.inbound_message_external_id or None,
        )
        session.add(
            TicketMessage(
                ticket_id=ticket.id,
                direction="outbound",
                author="cs-agent",
                body=reply,
                untrusted=False,
                created_at=utcnow(),
            )
        )
        ticket.status = "resolved"
        ticket.updated_at = utcnow()
        session.add(ticket)
        session.add(
            TicketAudit(
                ticket_id=ticket.id,
                action="auto_resolved",
                actor="cs-agent",
                detail="WISMO SOP applied; reply sent; auto-closed",
            )
        )
        await session.commit()
        return HandlingResult("auto_resolved", "resolved", True, "WISMO handled + auto-closed")

    async def _escalate(self, session: AsyncSession, ticket: Ticket, reason: str) -> HandlingResult:
        ticket.status = "needs_rep"
        ticket.updated_at = utcnow()
        session.add(ticket)
        session.add(
            TicketAudit(ticket_id=ticket.id, action="escalated", actor="cs-agent", detail=reason)
        )
        await session.commit()
        return HandlingResult("escalated", "needs_rep", False, reason)

    async def _lookup_order(self, order_ref: str | None) -> dict[str, Any] | None:
        if not order_ref:
            return None
        try:
            results = await self.shopify.search_orders(f"#{order_ref}", limit=1)
            return results[0] if results else None
        except Exception:  # noqa: BLE001 - lookup failure shouldn't crash handling
            logger.warning("order lookup failed for ref %s", order_ref)
            return None

    async def _evidence(
        self, session: AsyncSession, ticket: Ticket, kind: str, summary: str, data: dict[str, Any]
    ) -> None:
        session.add(TicketEvidence(ticket_id=ticket.id, kind=kind, summary=summary, data=data))
        await session.commit()


def _policy_excerpt(policy_text: str, *, limit: int = 360) -> str:
    text = " ".join(policy_text.replace("#", "").split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _tracking_url(policy_text: str, store_domain: str) -> str:
    m = _URL_RE.search(policy_text or "")
    if m:
        return m.group(0)
    return f"https://{store_domain}/account"
