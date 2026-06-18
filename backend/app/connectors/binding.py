"""Exact brand/store/connection/account binding (Invariant I-09).

Every connector read or write names the effective brand, store, connection, and
exact connected account. "Default", "latest", and "most recently connected" account
selection is forbidden for any supported operation. A binding that cannot resolve to
exactly one account is rejected with :class:`ConnectorBindingError` — including in
``unrestricted`` mode, because exact binding is technical integrity, not a business
guardrail (I-11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from app.connectors.errors import ConnectorBindingError

if TYPE_CHECKING:
    from app.connectors.models import Connection

#: Capability lanes a connection can serve (04-DATA §5.3).
Capability = Literal["store", "inbox", "ads", "payments", "supplier"]

#: Account references that can never identify an exact account for a write.
_FORBIDDEN_ACCOUNT_REFS = frozenset({"", "default", "latest", "any", "*", "most_recent"})


@dataclass(frozen=True)
class ConnectionBinding:
    """The exact, validated target of a connector operation.

    - ``brand_id``/``store_id``/``connection_id`` — the durable scope chain.
    - ``provider`` — adapter family (e.g. ``"direct"``, ``"composio"``); opaque to
      domain code and never the ontology.
    - ``capability`` — which lane this connection serves.
    - ``account_ref`` — the exact connected-account identifier (Composio
      connected_account_id, store domain for direct, etc.). Never a secret.
    - ``adapter_version`` — pins the adapter contract for traceability (I-19).
    """

    brand_id: UUID
    store_id: UUID
    connection_id: UUID
    provider: str
    capability: Capability
    account_ref: str
    adapter_version: str

    def __post_init__(self) -> None:
        for field_name in ("brand_id", "store_id", "connection_id"):
            if getattr(self, field_name) is None:
                raise ConnectorBindingError(f"binding requires {field_name}")
        if not self.provider:
            raise ConnectorBindingError("binding requires a provider")
        if not self.adapter_version:
            raise ConnectorBindingError("binding requires an adapter_version")
        self._validate_account_ref()

    def _validate_account_ref(self) -> None:
        ref = (self.account_ref or "").strip()
        if ref.lower() in _FORBIDDEN_ACCOUNT_REFS:
            raise ConnectorBindingError(
                "exact connected account required; default/latest/empty selection is "
                "forbidden for a supported operation",
                detail=f"provider={self.provider} capability={self.capability}",
            )

    @classmethod
    def from_connection(cls, connection: "Connection") -> "ConnectionBinding":
        """Build a binding from a stored connection record, failing closed.

        Rejects a connection that is not active or lacks an exact account_ref so a
        disconnected/ambiguous connection can never drive an operation.
        """
        if connection.status not in ("connected", "active", "degraded"):
            raise ConnectorBindingError(
                "connection is not usable",
                detail=f"connection_id={connection.id} status={connection.status}",
            )
        return cls(
            brand_id=connection.brand_id,
            store_id=connection.store_id,
            connection_id=connection.id,
            provider=connection.provider,
            capability=connection.capability,  # type: ignore[arg-type]
            account_ref=connection.account_ref,
            adapter_version=connection.adapter_version,
        )

    def require_account(self, expected_account_ref: str) -> None:
        """Assert this binding targets ``expected_account_ref``; else reject closed.

        Used by adapters to refuse a wrong-account operation (e.g. a fixture whose
        bound account does not match the credential/account actually resolved).
        """
        if self.account_ref != expected_account_ref:
            raise ConnectorBindingError(
                "bound account does not match the resolved account",
                detail=(
                    f"connection_id={self.connection_id} "
                    f"bound={self.account_ref} resolved={expected_account_ref}"
                ),
            )

    def scope_dict(self) -> dict[str, str]:
        """Secret-free scope for trace/evidence annotation."""
        return {
            "brand_id": str(self.brand_id),
            "store_id": str(self.store_id),
            "connection_id": str(self.connection_id),
            "provider": self.provider,
            "capability": self.capability,
            "account_ref": self.account_ref,
            "adapter_version": self.adapter_version,
        }
