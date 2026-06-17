"""Connector interfaces — the swappable boundary to external providers.

Design notes tied to the Invariants:

- **Invariant 2** is enforced *structurally*: `ShopifyConnector` exposes read methods
  and `create_discount` — and deliberately has **no refund method**. The CS agent is
  handed a `ShopifyConnector`, so it is incapable of issuing a refund. Refunds live in
  a separate `RefundExecutor` (see `refunds.py`) that requires an approved request and
  its own scoped connection. "Capability is defined by which tools exist."
- **Invariant 1**: connectors are constructed from a `ConnectionRef` (provider +
  external id). The raw token is resolved lazily and held as a `Secret`.
"""

from __future__ import annotations

import abc
from typing import Any

from .secrets import ConnectionRef


class ShopifyConnector(abc.ABC):
    """Read + discount surface for a single Shopify store.

    NOTE: there is intentionally no `refund(...)` / `cancel_order(...)` here. Adding
    one would violate Invariant 2 — refunds must go through `RefundExecutor`.
    """

    def __init__(self, ref: ConnectionRef) -> None:
        self.ref = ref

    # --- reads -------------------------------------------------------------
    @abc.abstractmethod
    async def get_shop(self) -> dict[str, Any]:
        """Return basic shop info; used by the health check."""

    @abc.abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Fetch a single order (WISMO lookup)."""

    @abc.abstractmethod
    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Find orders by name/email (e.g. for ticket-to-order matching)."""

    @abc.abstractmethod
    async def get_fulfillments(self, order_id: str) -> list[dict[str, Any]]:
        """Tracking/shipping status for an order (WISMO answer)."""

    # --- discounts (Tier 0/1 CS capability) --------------------------------
    @abc.abstractmethod
    async def create_discount(
        self, *, title: str, percentage: float, code: str
    ) -> dict[str, Any]:
        """Create a percentage discount code. The ONLY write the CS agent may do."""


class InboxConnector(abc.ABC):
    """Support-inbox surface (Gmail/Outlook via Composio)."""

    def __init__(self, ref: ConnectionRef) -> None:
        self.ref = ref

    @abc.abstractmethod
    async def health(self) -> dict[str, Any]:
        """Confirm the mailbox is reachable; used by the startup health check."""

    @abc.abstractmethod
    async def list_messages(self, *, unread_only: bool = True, limit: int = 25) -> list[dict[str, Any]]:
        """List recent inbound messages for ticket ingestion."""

    @abc.abstractmethod
    async def send_message(
        self, *, to: str, subject: str, body: str, in_reply_to: str | None = None
    ) -> dict[str, Any]:
        """Send an outbound reply (the CS agent's autonomous email)."""
