"""Default flows seeded for a new brand (Build Spec product direction).

Two flows ship out of the box — the merchant edits these (or adds their own) in the
dashboard. Wording lives in the step `message` fields; logic is the step order.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand
from app.models.flow import Flow

_ESCALATE = ["chargeback", "lawyer", "attorney", "fraud", "scam", "dispute", "police"]

WISMO_FLOW: dict[str, Any] = {
    "name": "Where is my order",
    "intent": "wismo",
    "triggers": [
        "where is my order", "where's my order", "wheres my order", "track",
        "tracking", "order status", "status of my order", "haven't received",
        "havent received", "not received", "still waiting", "wismo",
    ],
    "escalate_keywords": _ESCALATE,
    "position": 0,
    "steps": [
        {"type": "lookup_order"},
        {"type": "cite_policy", "slug": "shipping-policy"},
        {
            "type": "send_reply",
            "message": (
                "Hi {customer_name}, thanks for reaching out about {order_name}. "
                "{fulfillment_phrase}\n\nYou can see live delivery status any time on "
                "our tracking page: {tracking_url}\n\nPer our shipping policy: "
                "{policy_excerpt}\n\nIf anything still looks off after checking the "
                "tracking page, just reply here and we'll help.\n\nBest,\n{support_name}"
            ),
        },
        {"type": "resolve"},
    ],
}

REFUND_FLOW: dict[str, Any] = {
    "name": "Refund request",
    "intent": "refund",
    "triggers": [
        "refund", "money back", "return my order", "want my money",
        "cancel my order", "reimburse", "give me my money",
    ],
    "escalate_keywords": _ESCALATE,
    "position": 1,
    "steps": [
        {"type": "lookup_order"},
        {
            "type": "offer_discount",
            "percent": 10,
            "message": (
                "Hi {customer_name}, I'm sorry to hear that. Before we process a "
                "refund, I'd love to make it right — here's 10% off to keep "
                "{order_name}: {discount_code}. Would you like to keep it?"
            ),
            "accept_message": "Wonderful — {discount_code} is yours. Thanks for staying with us!",
        },
        {
            "type": "offer_discount",
            "percent": 20,
            "message": (
                "I completely understand. I can do better — here's 20% off: "
                "{discount_code}. Shall I apply that instead of refunding?"
            ),
            "accept_message": "Done — {discount_code} applied. Thank you so much!",
        },
        {
            "type": "request_refund_approval",
            "message": (
                "No problem at all, {customer_name}. I've sent your refund for "
                "{order_name} to our team for approval and we'll follow up shortly."
            ),
        },
    ],
}

DEFAULT_FLOWS = [WISMO_FLOW, REFUND_FLOW]


async def ensure_seed_flows(session: AsyncSession, brand: Brand) -> None:
    existing = (await session.exec(select(Flow).limit(1))).first()
    if existing is not None:
        return
    for spec in DEFAULT_FLOWS:
        session.add(
            Flow(
                brand_id=brand.id,
                name=spec["name"],
                intent=spec["intent"],
                triggers=spec["triggers"],
                escalate_keywords=spec["escalate_keywords"],
                steps=spec["steps"],
                position=spec["position"],
                enabled=True,
            )
        )
    await session.commit()
