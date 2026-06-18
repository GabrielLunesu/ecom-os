"""In-memory fake adapter for sandbox order retrieval and failure fixtures.

The fake backs every Ready-for-integration acceptance scenario without live
credentials:

- **sandbox order retrieval** — seeded normalized orders/customers/products.
- **wrong-account rejection** — the backend has a true ``account_ref`` and rejects
  any binding bound to a different account (I-09).
- **duplicate-once** — idempotent ``execute`` keyed by ``idempotency_intent_key``.
- **ambiguous outcome** — ``fail_mode="timeout"`` lands the side effect server-side
  but raises :class:`ConnectorTimeout`, so reconciliation can later confirm it
  without a second side effect (I-08).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import ConnectorBindingError, ConnectorTimeout, ConnectorUnavailable
from app.connectors.ports import (
    AttemptResult,
    CapabilityDescriptor,
    ConnectorPort,
    Evidence,
    ProviderCommand,
    payload_hash,
)
from app.core.time import utcnow

if TYPE_CHECKING:
    from app.connectors.registry import ConnectorRegistry

ADAPTER_VERSION = "fake-v1"


class FakeProviderBackend:
    """A stand-in upstream account holding normalized records + landed side effects."""

    def __init__(
        self,
        account_ref: str,
        *,
        orders: list[dict[str, Any]] | None = None,
        customers: list[dict[str, Any]] | None = None,
        products: list[dict[str, Any]] | None = None,
        fail_mode: str | None = None,
        unavailable: bool = False,
    ) -> None:
        self.account_ref = account_ref
        self.resources: dict[str, list[dict[str, Any]]] = {
            "orders": orders or [],
            "customers": customers or [],
            "products": products or [],
        }
        # intent_key -> provider_operation_id for side effects that actually landed.
        self.landed: dict[str, str] = {}
        self.execute_calls = 0
        self.fail_mode = fail_mode
        self.unavailable = unavailable

    def by_id(self, resource: str, external_id: str) -> dict[str, Any] | None:
        for rec in self.resources.get(resource, []):
            if str(rec.get("external_id")) == str(external_id):
                return rec
        return None


class FakeCommerceAdapter(ConnectorPort):
    """Provider-independent fake bound to exactly one :class:`FakeProviderBackend`."""

    def __init__(self, binding: ConnectionBinding, backend: FakeProviderBackend) -> None:
        super().__init__(binding)
        self._backend = backend
        self.descriptor = CapabilityDescriptor(
            provider=binding.provider,
            capability=binding.capability,
            read_operations=("orders", "customers", "products"),
            write_operations=("create_discount",),
            supports_idempotency=True,
            supports_reconciliation=True,
            sandbox=True,
        )

    def _guard(self) -> None:
        # Exact-account enforcement: the bound account must match the real account.
        self.binding.require_account(self._backend.account_ref)
        if self._backend.unavailable:
            raise ConnectorUnavailable("fake backend marked unavailable")

    async def health(self) -> dict[str, Any]:
        # Probe the exact account; reject a wrong-account binding even for health.
        self.binding.require_account(self._backend.account_ref)
        if self._backend.unavailable:
            raise ConnectorUnavailable("fake backend marked unavailable")
        return {
            "provider": self.binding.provider,
            "account_ref": self._backend.account_ref,
            "status": "ACTIVE",
        }

    async def fetch(
        self, resource: str, *, cursor: str | None = None, limit: int = 250
    ) -> tuple[list[dict[str, Any]], str | None]:
        self._guard()
        records = self._backend.resources.get(resource, [])
        start = int(cursor) if cursor else 0
        page = records[start : start + limit]
        next_cursor = str(start + limit) if start + limit < len(records) else None
        return list(page), next_cursor

    async def fetch_one(self, resource: str, external_id: str) -> dict[str, Any] | None:
        self._guard()
        rec = self._backend.by_id(resource, external_id)
        return dict(rec) if rec is not None else None

    async def execute(self, command: ProviderCommand) -> AttemptResult:
        self._guard()
        self._backend.execute_calls += 1
        key = command.idempotency_intent_key
        # Idempotency: a previously-landed intent returns the same provider id; no
        # second side effect (I-07).
        if key in self._backend.landed:
            op_id = self._backend.landed[key]
            return AttemptResult(
                outcome_confidence="confirmed",
                provider_operation_id=op_id,
                summary={"deduplicated": True},
            )
        op_id = f"op_{payload_hash(command.digest())[7:19]}"
        if self._backend.fail_mode == "timeout":
            # The write landed upstream, but we never saw the confirmation.
            self._backend.landed[key] = op_id
            raise ConnectorTimeout(
                "provider timed out after dispatch; outcome unknown",
                detail=f"operation={command.operation}",
            )
        self._backend.landed[key] = op_id
        ev = Evidence(
            source=self.binding.provider,
            source_id=op_id,
            source_timestamp=None,
            collected_timestamp=utcnow(),
            trust_label="untrusted",
            content_hash=command.digest(),
            reference=f"{self.binding.provider}:{op_id}",
        )
        return AttemptResult(
            outcome_confidence="confirmed", provider_operation_id=op_id, evidence=[ev]
        )

    async def reconcile(self, command: ProviderCommand) -> AttemptResult:
        # Reconcile against the exact account; query whether the intent landed.
        self.binding.require_account(self._backend.account_ref)
        key = command.idempotency_intent_key
        if key in self._backend.landed:
            op_id = self._backend.landed[key]
            return AttemptResult(
                outcome_confidence="confirmed",
                provider_operation_id=op_id,
                summary={"reconciled": True},
            )
        return AttemptResult(
            outcome_confidence="failed", provider_operation_id=None, summary={"reconciled": True}
        )


def assert_bound(binding: ConnectionBinding, account_ref: str) -> None:
    """Helper used by fixtures to document the wrong-account expectation."""
    if binding.account_ref != account_ref:
        raise ConnectorBindingError("wrong account")


def build_fake_registry(
    backends: dict[str, FakeProviderBackend], *, capability: str = "store", provider: str = "fake"
) -> "ConnectorRegistry":
    """Build a registry whose fake adapter is bound to the backend for its account.

    Resolving a binding whose ``account_ref`` has no backend raises
    :class:`ConnectorBindingError` — i.e. an unknown account fails closed.
    """
    from app.connectors.registry import ConnectorRegistry

    def factory(binding: ConnectionBinding) -> FakeCommerceAdapter:
        backend = backends.get(binding.account_ref)
        if backend is None:
            raise ConnectorBindingError(
                "no connected account matches this binding",
                detail=f"account_ref={binding.account_ref}",
            )
        return FakeCommerceAdapter(binding, backend)

    reg = ConnectorRegistry()
    reg.register(provider, capability, factory)
    return reg
