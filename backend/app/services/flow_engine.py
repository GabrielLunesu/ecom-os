"""Flow engine — runs a merchant-configured CS flow against a ticket.

A flow is an ordered list of deterministic steps. The engine executes them until it
must wait for the customer (awaiting_customer), resolves, or escalates to a rep. Only
the customer-facing wording is templated — the control flow is plain if-statements.

Structural invariants (not configurable):
- Discounts are capped (Inv-safe); a flow can offer them but the cap is enforced here.
- A flow can FILE a refund into the approval lane (`request_refund_approval`) but can
  NEVER execute one — RefundExecutor is never imported or called here (Invariant 2).
- `escalate_keywords` and unhandled cases hand off to a human; once needs_rep a flow
  never resumes (Invariant 3). The inbound text is untrusted data (Invariant 4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.core.time import utcnow
from app.models.brand import Brand
from app.models.flow import Flow
from app.models.tickets import Ticket, TicketAudit, TicketEvidence, TicketMessage
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.tickets import ticket_messages
from app.services.vault import get_document

logger = get_logger(__name__)

MAX_DISCOUNT = 20.0
_ORDER_RE = re.compile(r"#?\s*(\d{3,})")
_ACCEPT = (
    "yes", "yeah", "yep", "ok", "okay", "sure", "keep", "deal", "sounds good",
    "apply", "accept", "i'll keep", "ill keep", "fine", "great",
)
# Statuses a flow never resumes from (sticky escalation / closed).
_FROZEN = ("needs_rep", "resolved")


@dataclass
class FlowOutcome:
    kind: str  # "continue" | "wait" | "resolve" | "escalate"
    reason: str = ""


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:  # leave unknown placeholders intact
        return "{" + key + "}"


def _render(template: str, vars_: dict[str, Any]) -> str:
    return template.format_map(_SafeDict(vars_))


def classify_flow(flows: list[Flow], subject: str, body: str) -> Flow | None:
    """Pick the first enabled flow whose trigger keywords match (by position)."""
    text = f"{subject}\n{body}".lower()
    matches = [
        f
        for f in flows
        if f.enabled and any(t.lower() in text for t in (f.triggers or []))
    ]
    matches.sort(key=lambda f: f.position)
    return matches[0] if matches else None


def _fulfillment_phrase(order: dict[str, Any] | None) -> str:
    status = (order.get("fulfillment_status") or "unfulfilled") if order else "unfulfilled"
    return {
        "fulfilled": "Your order has shipped.",
        "partial": "Part of your order has shipped; the rest is on the way.",
    }.get(status, "Your order is being prepared and has not shipped yet.")


class FlowEngine:
    """Executes flows. Holds read+discount Shopify + the inbox — never a refund tool."""

    def __init__(self, shopify: ShopifyConnector, inbox: InboxConnector, store_domain: str):
        self.shopify = shopify
        self.inbox = inbox
        self.store_domain = store_domain

    # --- public entry points -------------------------------------------------
    async def run(self, session: AsyncSession, ticket: Ticket, flow: Flow) -> FlowOutcome:
        """Start or resume `flow` on `ticket` based on its current flow_step."""
        if ticket.status in _FROZEN:
            return FlowOutcome("escalate", "frozen (sticky escalation)")

        body = await self._inbound_body(session, ticket)

        # Escalate immediately on hard keywords at any turn.
        if any(k.lower() in body.lower() for k in (flow.escalate_keywords or [])):
            return await self._escalate(session, ticket, "escalation keyword in customer message")

        data: dict[str, Any] = dict(ticket.flow_data or {})
        steps = flow.steps or []
        i = ticket.flow_step

        # If we were waiting on a step, resolve that branch first.
        if data.get("awaiting_step") == i and i < len(steps):
            branch = await self._resume_step(session, ticket, steps[i], data, body)
            if branch.kind != "continue":
                return await self._persist_and_finish(session, ticket, data, i, branch)
            i += 1  # advance past the resolved wait-step

        # Run forward until wait / resolve / escalate / end.
        while i < len(steps):
            outcome = await self._run_step(session, ticket, steps[i], data, body)
            if outcome.kind == "wait":
                data["awaiting_step"] = i
                return await self._persist_and_finish(session, ticket, data, i, outcome)
            if outcome.kind in ("resolve", "escalate"):
                return await self._persist_and_finish(session, ticket, data, i, outcome)
            i += 1  # continue

        return await self._persist_and_finish(
            session, ticket, data, max(i - 1, 0), FlowOutcome("resolve", "flow complete")
        )

    # --- step dispatch -------------------------------------------------------
    async def _run_step(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any], body: str
    ) -> FlowOutcome:
        kind = step.get("type")
        if kind == "lookup_order":
            return await self._step_lookup_order(session, ticket, data, body)
        if kind == "cite_policy":
            return await self._step_cite_policy(session, ticket, step, data)
        if kind == "send_reply":
            return await self._step_send_reply(session, ticket, step, data)
        if kind == "offer_discount":
            return await self._step_offer_discount(session, ticket, step, data)
        if kind == "request_refund_approval":
            return await self._step_request_refund(session, ticket, step, data)
        if kind == "escalate":
            return FlowOutcome("escalate", step.get("reason", "flow escalate step"))
        if kind == "resolve":
            return FlowOutcome("resolve", "flow resolve step")
        logger.warning("unknown flow step type: %s", kind)
        return FlowOutcome("escalate", f"unknown step type {kind}")

    async def _resume_step(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any], body: str
    ) -> FlowOutcome:
        """Branch on a customer reply for a waiting step. Default = advance (continue)."""
        if step.get("type") == "offer_discount":
            if _looks_like_acceptance(body):
                await self._send(session, ticket, step.get("accept_message", "Great — your discount is applied. Thanks for staying with us!"), data)
                return FlowOutcome("resolve", "customer accepted the offer")
            return FlowOutcome("continue", "customer declined; advancing")
        return FlowOutcome("continue", "resume advance")

    # --- steps ---------------------------------------------------------------
    async def _step_lookup_order(
        self, session: AsyncSession, ticket: Ticket, data: dict[str, Any], body: str
    ) -> FlowOutcome:
        ref = _extract_order_ref(f"{ticket.subject}\n{body}")
        order: dict[str, Any] | None = None
        try:
            query = f"#{ref}" if ref else ticket.customer_email
            results = await self.shopify.search_orders(query, limit=1)
            order = results[0] if results else None
        except Exception:  # noqa: BLE001
            logger.warning("flow order lookup failed")
        data["order_ref"] = ref
        data["order_name"] = (order or {}).get("name") or (f"#{ref}" if ref else "your order")
        data["order_id"] = str((order or {}).get("id") or "")
        data["order_total"] = float((order or {}).get("total_price") or 0)
        data["fulfillment_phrase"] = _fulfillment_phrase(order)
        await self._evidence(session, ticket, "order_lookup", data["order_name"], {"found": bool(order)})
        return FlowOutcome("continue")

    async def _step_cite_policy(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any]
    ) -> FlowOutcome:
        slug = step.get("slug", "shipping-policy")
        doc = await get_document(session, slug)
        text = " ".join((doc.body if doc else "").replace("#", "").split())
        data["policy_excerpt"] = text[:320] + ("…" if len(text) > 320 else "")
        m = re.search(r"https?://[^\s)]+", doc.body if doc else "")
        data["tracking_url"] = m.group(0) if m else f"https://{self.store_domain}/account"
        await self._evidence(session, ticket, "policy_cite", slug, {"slug": slug})
        await self._evidence(session, ticket, "tracking", data["tracking_url"], {"url": data["tracking_url"]})
        return FlowOutcome("continue")

    async def _step_send_reply(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any]
    ) -> FlowOutcome:
        await self._send(session, ticket, step.get("message", ""), data)
        return FlowOutcome("continue")

    async def _step_offer_discount(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any]
    ) -> FlowOutcome:
        pct = min(float(step.get("percent", 10)), MAX_DISCOUNT)
        code = f"SAVE{int(pct)}-{str(ticket.id)[:6].upper()}"
        try:
            await self.shopify.create_discount(title=f"CS offer {int(pct)}%", percentage=pct, code=code)
        except Exception:  # noqa: BLE001
            logger.warning("discount creation failed; offering code anyway")
        data["discount_code"] = code
        data["discount_percent"] = int(pct)
        await self._evidence(session, ticket, "discount_offer", f"{int(pct)}% {code}", {"percent": pct})
        await self._send(session, ticket, step.get("message", "Here's {discount_percent}% off: {discount_code}"), data)
        return FlowOutcome("wait", "awaiting customer decision on discount")

    async def _step_request_refund(
        self, session: AsyncSession, ticket: Ticket, step: dict[str, Any], data: dict[str, Any]
    ) -> FlowOutcome:
        # FILE a refund into the approval lane — NEVER execute one (Invariant 2).
        from app.services.refunds import create_refund_request

        brand = await session.get(Brand, ticket.brand_id)
        if brand is not None:
            await create_refund_request(
                session,
                brand=brand,
                order_id=str(data.get("order_id", "")),
                order_name=str(data.get("order_name", "")),
                amount=float(data.get("order_total", 0)),
                currency="USD",
                reason="customer refund request (CS flow)",
                requested_by="cs-flow",
                ticket_id=ticket.id,
            )
        await self._evidence(session, ticket, "refund_filed", str(data.get("order_name", "")), {"approval_lane": True})
        await self._send(session, ticket, step.get("message", "I've sent your refund to our team for approval; we'll be in touch shortly."), data)
        # Hand to a human to approve the refund (sticky escalation).
        return FlowOutcome("escalate", "refund filed; awaiting human approval")

    # --- effects -------------------------------------------------------------
    async def _send(
        self, session: AsyncSession, ticket: Ticket, template: str, data: dict[str, Any]
    ) -> None:
        body = _render(template, {"customer_name": (ticket.customer_name or "there").split(" ")[0], **data})
        await self.inbox.send_message(
            to=ticket.customer_email,
            subject=f"Re: {ticket.subject}",
            body=body,
            in_reply_to=ticket.inbound_message_external_id or None,
        )
        session.add(
            TicketMessage(ticket_id=ticket.id, direction="outbound", author="cs-flow", body=body, untrusted=False, created_at=utcnow())
        )
        await session.commit()

    async def _evidence(
        self, session: AsyncSession, ticket: Ticket, kind: str, summary: str, payload: dict[str, Any]
    ) -> None:
        session.add(TicketEvidence(ticket_id=ticket.id, kind=kind, summary=summary, data=payload))
        await session.commit()

    async def _escalate(self, session: AsyncSession, ticket: Ticket, reason: str) -> FlowOutcome:
        return await self._persist_and_finish(
            session, ticket, dict(ticket.flow_data or {}), ticket.flow_step, FlowOutcome("escalate", reason)
        )

    async def _persist_and_finish(
        self, session: AsyncSession, ticket: Ticket, data: dict[str, Any], step_index: int, outcome: FlowOutcome
    ) -> FlowOutcome:
        ticket.flow_step = step_index
        ticket.flow_data = data
        if outcome.kind == "wait":
            ticket.status = "awaiting_customer"
        elif outcome.kind == "resolve":
            ticket.status = "resolved"
        elif outcome.kind == "escalate":
            ticket.status = "needs_rep"
        ticket.updated_at = utcnow()
        session.add(ticket)
        session.add(
            TicketAudit(ticket_id=ticket.id, action=f"flow_{outcome.kind}", actor="cs-flow", detail=outcome.reason)
        )
        await session.commit()
        return outcome

    async def _inbound_body(self, session: AsyncSession, ticket: Ticket) -> str:
        msgs = await ticket_messages(session, ticket.id)
        inbound = [m for m in msgs if m.direction == "inbound"]
        return inbound[-1].body if inbound else ""


def _extract_order_ref(text: str) -> str | None:
    m = _ORDER_RE.search(text or "")
    return m.group(1) if m else None


def _looks_like_acceptance(body: str) -> bool:
    t = (body or "").lower()
    return any(w in t for w in _ACCEPT)


async def list_flows(session: AsyncSession) -> list[Flow]:
    return list((await session.exec(select(Flow).order_by(Flow.position))).all())  # type: ignore[arg-type]


async def update_flow(
    session: AsyncSession,
    flow_id: UUID,
    *,
    name: str,
    enabled: bool,
    triggers: list[str],
    escalate_keywords: list[str],
    steps: list[dict[str, Any]],
) -> Flow | None:
    flow = (await session.exec(select(Flow).where(Flow.id == flow_id))).first()
    if flow is None:
        return None
    flow.name = name
    flow.enabled = enabled
    flow.triggers = triggers
    flow.escalate_keywords = escalate_keywords
    flow.steps = steps
    flow.updated_at = utcnow()
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return flow
