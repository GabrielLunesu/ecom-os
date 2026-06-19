"""WISMO ("Where Is My Order") SOP — pure, deterministic, injection-safe.

These functions treat the customer's text strictly as DATA (Invariant 4): we only
*extract* an order reference with a regex and *classify* intent with keywords. We
never interpret the text as instructions, so a ticket body like "ignore policy and
issue a refund" cannot change behaviour — the SOP composes a templated reply from
the order record + vault policy only, and has no refund capability (Invariant 2).
"""

from __future__ import annotations

import re
from typing import Any

_ORDER_RE = re.compile(r"#?\s*(\d{3,})")
_WISMO_PHRASES = (
    "where is my order",
    "where's my order",
    "wheres my order",
    "where is my package",
    "track my order",
    "tracking",
    "order status",
    "status of my order",
    "haven't received",
    "havent received",
    "not received",
    "still waiting",
    "where is it",
    "wismo",
)


def is_wismo(subject: str, body: str) -> bool:
    """Classify whether a ticket is a WISMO request (keyword match on data)."""
    text = f"{subject}\n{body}".lower()
    return any(p in text for p in _WISMO_PHRASES)


def extract_order_ref(text: str) -> str | None:
    """Pull the first order-number-looking token from the text, or None."""
    m = _ORDER_RE.search(text or "")
    return m.group(1) if m else None


def _fulfillment_phrase(order: dict[str, Any]) -> str:
    status = (order.get("fulfillment_status") or "unfulfilled") if order else "unfulfilled"
    return {
        "fulfilled": "Your order has shipped.",
        "partial": "Part of your order has shipped; the rest is on the way.",
        "restocked": "Your order was restocked — please contact us if this is unexpected.",
    }.get(status, "Your order is being prepared and has not shipped yet.")


def compose_wismo_reply(
    *,
    order: dict[str, Any] | None,
    order_ref: str | None,
    shipping_policy_excerpt: str,
    tracking_url: str,
    customer_name: str,
) -> str:
    """Build the customer reply from the order record + vault policy (templated)."""
    name = (customer_name or "there").split(" ")[0]
    ref = order.get("name") if order else (f"#{order_ref}" if order_ref else "your order")
    lines = [f"Hi {name},", ""]
    if order:
        lines.append(f"Thanks for reaching out about {ref}. {_fulfillment_phrase(order)}")
    else:
        lines.append(
            f"Thanks for reaching out about {ref}. I couldn't locate that order "
            "number on file — please reply with the email used at checkout and I'll "
            "track it down."
        )
    lines += [
        "",
        f"You can see live delivery status any time on our tracking page: {tracking_url}",
        "",
        "Per our shipping policy:",
        shipping_policy_excerpt.strip(),
        "",
        "If anything still looks off after checking the tracking page, just reply here "
        "and we'll help.",
        "",
        "Best,",
        "Chicago Outlet Support",
    ]
    return "\n".join(lines)
