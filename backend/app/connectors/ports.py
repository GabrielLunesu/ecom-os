"""Connector contract value types and the :class:`ConnectorPort` interface.

These types are the public boundary between A04 and its consumers (A02/A05/A08).
Raw provider payloads never appear here — only normalized records, evidence
references, and coverage/freshness labels (04-DATA §4, §7, §9).
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Generic, Literal, TypeVar

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import OutcomeConfidence
from app.core.time import utcnow

T = TypeVar("T")

#: Honest trace coverage labels (ADR-009 / I-12).
Coverage = Literal["verified", "observed", "imported", "unknown"]

#: How current a read is relative to its source.
FreshnessStatus = Literal["current", "stale", "partial"]


@dataclass(frozen=True)
class Evidence:
    """A pointer to the upstream proof behind a normalized value (04-DATA §9).

    Holds a reference and a content hash, never the raw payload itself, so evidence
    can be cited without leaking provider shapes into a public contract.
    """

    source: str
    source_id: str
    source_timestamp: datetime | None
    collected_timestamp: datetime
    trust_label: Literal["trusted", "untrusted"]
    content_hash: str
    reference: str = ""
    excerpt: str = ""

    @classmethod
    def for_payload(
        cls,
        *,
        source: str,
        source_id: str,
        payload: dict[str, Any],
        source_timestamp: datetime | None,
        trust_label: Literal["trusted", "untrusted"] = "untrusted",
        reference: str = "",
    ) -> "Evidence":
        return cls(
            source=source,
            source_id=source_id,
            source_timestamp=source_timestamp,
            collected_timestamp=utcnow(),
            trust_label=trust_label,
            content_hash=payload_hash(payload),
            reference=reference or f"{source}:{source_id}",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "collected_timestamp": self.collected_timestamp.isoformat(),
            "trust_label": self.trust_label,
            "content_hash": self.content_hash,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class Freshness:
    """Freshness of a read: when it was last synced and whether it is current."""

    as_of: datetime | None
    status: FreshnessStatus

    def to_dict(self) -> dict[str, object]:
        return {"as_of": self.as_of.isoformat() if self.as_of else None, "status": self.status}

    @classmethod
    def from_sync(
        cls,
        synced_at: datetime | None,
        *,
        now: datetime | None = None,
        stale_after: timedelta = timedelta(minutes=15),
        degraded: bool = False,
        partial: bool = False,
    ) -> "Freshness":
        """Derive freshness from the last successful sync time.

        ``degraded`` (connection unhealthy / outage) forces ``stale`` so an outage
        can never present last-good data as current (05-OPS §11.2).
        """
        now = now or utcnow()
        if synced_at is None:
            return cls(as_of=None, status="partial")
        if partial:
            return cls(as_of=synced_at, status="partial")
        if degraded or (now - synced_at) > stale_after:
            return cls(as_of=synced_at, status="stale")
        return cls(as_of=synced_at, status="current")


@dataclass(frozen=True)
class ReadResult(Generic[T]):
    """A read value plus its provenance (BUILD §4 cross-cutting contract)."""

    data: T
    freshness: Freshness
    coverage: Coverage
    evidence: list[Evidence] = field(default_factory=list)

    def to_envelope(self) -> dict[str, object]:
        data: Any = self.data
        if hasattr(data, "to_view"):
            data = data.to_view()
        elif isinstance(data, list):
            data = [d.to_view() if hasattr(d, "to_view") else d for d in data]
        return {
            "data": data,
            "freshness": self.freshness.to_dict(),
            "coverage": self.coverage,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass(frozen=True)
class ProviderCommand:
    """A normalized external-write request (the input to ``ConnectorPort.execute``).

    The connector never invents a side effect: ``operation`` and ``arguments`` are
    normalized domain values, and ``idempotency_intent_key`` ties the command to one
    operator/agent intent so retries cannot duplicate a side effect (I-07, 04 §8.4).
    """

    operation: str
    arguments: dict[str, Any]
    idempotency_intent_key: str

    def digest(self) -> str:
        """A stable digest over operation + normalized arguments (AGENTS.md §5)."""
        return payload_hash({"operation": self.operation, "arguments": self.arguments})


@dataclass(frozen=True)
class AttemptResult:
    """The outcome of a single connector attempt (04-DATA §8.3).

    ``provider_operation_id`` is the upstream id used for reconciliation; ``evidence``
    cites the upstream confirmation. A timeout produces ``outcome_confidence="unknown"``
    with no confirmation — never a silent success.
    """

    outcome_confidence: OutcomeConfidence
    provider_operation_id: str | None
    evidence: list[Evidence] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.outcome_confidence == "confirmed"


@dataclass(frozen=True)
class CapabilityDescriptor:
    """What an adapter declares about itself (AGENTS.md §8)."""

    provider: str
    capability: str
    read_operations: tuple[str, ...]
    write_operations: tuple[str, ...]
    supports_idempotency: bool
    supports_reconciliation: bool
    sandbox: bool


class ConnectorPort(abc.ABC):
    """Provider-independent connector contract.

    Reads return normalized dicts (the sync layer maps them to rows + evidence).
    Writes go through :meth:`execute`, and ambiguous outcomes are resolved through
    :meth:`reconcile`. Adapters declare their capabilities via :attr:`descriptor`.
    """

    descriptor: CapabilityDescriptor

    def __init__(self, binding: ConnectionBinding) -> None:
        self.binding = binding

    @abc.abstractmethod
    async def health(self) -> dict[str, Any]:
        """Probe the EXACT bound account (not just the provider API). Secret-free."""

    @abc.abstractmethod
    async def fetch(
        self, resource: str, *, cursor: str | None = None, limit: int = 250
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return ``(normalized_records, next_cursor)`` for a resource page.

        ``next_cursor`` is ``None`` on the last page. Records are normalized domain
        dicts, not raw provider payloads.
        """

    @abc.abstractmethod
    async def fetch_one(self, resource: str, external_id: str) -> dict[str, Any] | None:
        """Fetch a single normalized record by its provider external id, or None."""

    async def execute(self, command: ProviderCommand) -> AttemptResult:
        """Perform one external write. Default: the adapter declares no writes."""
        from app.connectors.errors import CapabilityUnsupported

        raise CapabilityUnsupported(
            f"{self.descriptor.provider}/{self.descriptor.capability} supports no writes",
        )

    async def reconcile(self, command: ProviderCommand) -> AttemptResult:
        """Query the provider for the outcome of a prior ambiguous attempt.

        Returns ``outcome_confidence="confirmed"`` with the discovered provider id if
        the side effect exists, ``"failed"`` if it provably does not, or ``"unknown"``
        if still indeterminate. Never repeats the side effect.
        """
        from app.connectors.errors import CapabilityUnsupported

        raise CapabilityUnsupported(
            f"{self.descriptor.provider}/{self.descriptor.capability} has no reconciler",
        )


def payload_hash(payload: Any) -> str:
    """Stable SHA-256 over a JSON-serializable payload (sorted keys)."""
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def to_minor_units(amount: str | float | int | None, *, places: int = 2) -> int:
    """Convert a decimal money amount to integer minor units (I-16).

    Uses string/Decimal math to avoid float drift. ``None`` -> 0.
    """
    from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

    if amount is None or amount == "":
        return 0
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return 0
    quant = Decimal(10) ** -places
    minor = (value / quant).to_integral_value(rounding=ROUND_HALF_UP)
    return int(minor)
