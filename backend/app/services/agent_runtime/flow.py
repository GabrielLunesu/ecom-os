"""FlowCSRuntime — runs merchant-configured flows behind the AgentRuntime interface.

Classification routes a new ticket to a flow; a resuming ticket (one that already has
a flow_id from a prior customer turn) continues where it left off. Like every CS
runtime it holds read + discount tools only — never a refund executor (Invariant 2).
"""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.models.tickets import Ticket
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.flow_engine import FlowEngine, classify_flow, list_flows
from app.services.tickets import ticket_messages

from .base import AgentRuntime, HandlingResult

logger = get_logger(__name__)
_FROZEN = ("needs_rep", "resolved")
_ACTION = {"resolve": "auto_resolved", "escalate": "escalated", "wait": "awaiting"}


class FlowCSRuntime(AgentRuntime):
    def __init__(self, shopify: ShopifyConnector, inbox: InboxConnector, store_domain: str):
        self.engine = FlowEngine(shopify=shopify, inbox=inbox, store_domain=store_domain)

    async def handle_ticket(self, session: AsyncSession, ticket: Ticket) -> HandlingResult:
        if ticket.status in _FROZEN:
            return HandlingResult("skipped", ticket.status, False, "frozen (sticky escalation)")

        flows = await list_flows(session)

        if ticket.flow_id is not None:  # resuming an in-progress flow
            flow = next((f for f in flows if f.id == ticket.flow_id), None)
            if flow is None:
                return await self._escalate(session, ticket, "flow no longer exists")
        else:  # new ticket — classify
            msgs = await ticket_messages(session, ticket.id)
            body = next((m.body for m in msgs if m.direction == "inbound"), "")
            flow = classify_flow(flows, ticket.subject, body)
            if flow is None:
                return await self._escalate(session, ticket, "no matching flow; needs a rep")
            ticket.flow_id = flow.id
            ticket.flow_step = 0
            ticket.flow_data = {}
            session.add(ticket)
            await session.commit()

        outcome = await self.engine.run(session, ticket, flow)
        action = _ACTION.get(outcome.kind, "skipped")
        return HandlingResult(action, ticket.status, action == "auto_resolved", outcome.reason)

    async def _escalate(self, session: AsyncSession, ticket: Ticket, reason: str) -> HandlingResult:
        from app.core.time import utcnow
        from app.models.tickets import TicketAudit

        ticket.status = "needs_rep"
        ticket.updated_at = utcnow()
        session.add(ticket)
        session.add(TicketAudit(ticket_id=ticket.id, action="escalated", actor="cs-flow", detail=reason))
        await session.commit()
        return HandlingResult("escalated", "needs_rep", False, reason)
