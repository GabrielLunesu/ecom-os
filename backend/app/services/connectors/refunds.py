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

from .secrets import ConnectionRef, Secret, env_or_setting, resolve_secret

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
        return resolve_secret(REFUND_TOKEN_HANDLE)

    async def execute(self, approval: RefundApproval | None) -> dict[str, object]:
        if approval is None:
            raise RefundNotApprovedError(
                "refunds require an approved RefundApproval (Invariant 2)",
            )
        # Slice 11 performs the Shopify refund mutation here using self._token().
        raise NotImplementedError(
            "refund execution lands in build slice 11; the approval gate is enforced",
        )
