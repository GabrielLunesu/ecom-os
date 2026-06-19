"""Refund executor — the ONLY path that can issue a Shopify refund.

Invariant 2: refunds are separate from the CS agent. This executor:
  1. is not a `ShopifyConnector` and is never handed to the CS agent;
  2. refuses to act without an explicit approval record (the approval lane);
  3. resolves its own scoped credential handle, distinct from the CS connection.

The actual Shopify refund mutation is wired in build slice 11; this module fixes
the boundary and the approval gate first (tests-first).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .secrets import ConnectionRef, Secret, env_or_setting, resolve_secret

_API_VERSION = "2025-01"
_TIMEOUT = httpx.Timeout(30.0)

# Distinct handle so the refund path uses its own scoped connection. In production
# this is a second Shopify app limited to write_orders; see docs/ecom-os/bootstrap.md.
REFUND_TOKEN_HANDLE = "SHOPIFY_REFUND_ACCESS_TOKEN"


class RefundNotApprovedError(PermissionError):
    """Raised when a refund is attempted without an approval record."""


@dataclass(frozen=True)
class RefundApproval:
    """Proof that a human approved a specific refund via the approval lane."""

    approval_id: str
    order_id: str
    amount: float
    approved_by: str


class RefundExecutor:
    """Approval-gated refund path with its own scoped connection (Invariant 2)."""

    def __init__(self, ref: ConnectionRef) -> None:
        self.ref = ref

    @classmethod
    def from_env(cls) -> "RefundExecutor":
        domain = env_or_setting("SHOPIFY_STORE_URL")
        if not domain:
            raise RuntimeError("SHOPIFY_STORE_URL is not set")
        return cls(ConnectionRef(provider="direct", external_id=domain))

    def _token(self) -> Secret:
        # Distinct, scoped token (Invariant 2). Raises if the refund app isn't
        # provisioned — refunds simply cannot run without their own connection.
        return resolve_secret(REFUND_TOKEN_HANDLE)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=f"https://{self.ref.external_id}/admin/api/{_API_VERSION}",
            headers={
                "X-Shopify-Access-Token": self._token().reveal(),
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )

    async def execute(self, approval: RefundApproval | None) -> dict[str, Any]:
        """Issue a Shopify refund — ONLY for an approved request (Invariant 2)."""
        if approval is None:
            raise RefundNotApprovedError(
                "refunds require an approved RefundApproval (Invariant 2)",
            )
        async with self._client() as client:
            # Find the capturing transaction to refund against.
            tx_resp = await client.get(f"/orders/{approval.order_id}/transactions.json")
            tx_resp.raise_for_status()
            txns = tx_resp.json().get("transactions", [])
            parent = next(
                (
                    t
                    for t in txns
                    if t.get("kind") in ("sale", "capture") and t.get("status") == "success"
                ),
                None,
            )
            if parent is None:
                raise RuntimeError("no capturing transaction found to refund")
            payload = {
                "refund": {
                    "notify": False,
                    "note": f"approved refund ({approval.approval_id}) by {approval.approved_by}",
                    "transactions": [
                        {
                            "parent_id": parent["id"],
                            "amount": f"{approval.amount:.2f}",
                            "kind": "refund",
                            "gateway": parent.get("gateway"),
                        }
                    ],
                }
            }
            resp = await client.post(f"/orders/{approval.order_id}/refunds.json", json=payload)
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
            return body
