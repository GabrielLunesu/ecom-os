"""The canonical tool catalog and its definition type (Runtime Spec §6.1).

A ``ToolDefinition`` carries the required metadata for one tool and a deterministic
``schema_hash``. ``ToolCatalog`` is the single registry from which adapter and MCP
schemas are generated; its ``compatibility_hash`` lets the conformance suite detect any
drift between the two surfaces.

This module is intentionally free of ecommerce execution logic. Domain agents (A04/A05/
A07/A08) own the handlers; they register their owned ``ToolDefinition`` objects without
hand-maintaining duplicate adapter/MCP schemas.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum

# A stable tool name: ``ecom.<namespace>.<verb>`` (Runtime Spec §6.1).
_NAME_RE = re.compile(r"^ecom\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

# Verbs that mutate external/business state. A tool using one of these MUST be a write
# tool — this catches the "read tool that opportunistically writes" anti-pattern.
_WRITE_VERBS: frozenset[str] = frozenset(
    {
        "create",
        "update",
        "delete",
        "send",
        "execute",
        "cancel",
        "refund",
        "void",
        "apply",
        "set",
        "propose",
    }
)


class ReadOrWrite(str, Enum):
    read = "read"
    write = "write"


class RiskClass(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Coverage(str, Enum):
    """Honest trace coverage labels (AGENTS I-12, Runtime §7.2)."""

    verified = "verified"
    observed = "observed"
    imported = "imported"
    unknown = "unknown"


class ReconciliationStrategy(str, Enum):
    none = "none"
    provider_lookup = "provider_lookup"
    idempotency_key = "idempotency_key"


def _canonical_json(value: object) -> str:
    """Stable JSON used for hashing (sorted keys, no incidental whitespace)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ToolDefinition:
    """One canonical tool. All fields map to Runtime Spec §6.1 required metadata."""

    name: str
    version: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    read_or_write: ReadOrWrite
    risk_class: RiskClass
    required_ecom_permissions: tuple[str, ...] = ()
    required_connection_types: tuple[str, ...] = ()
    store_scope_rule: str = "none"  # "none" | "optional" | "required"
    supports_simulation: bool = False
    supports_idempotency: bool = False
    reconciliation_strategy: ReconciliationStrategy = ReconciliationStrategy.none
    sensitive_fields: tuple[str, ...] = ()
    minimum_trace_coverage: Coverage = Coverage.verified

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError(f"tool name {self.name!r} must match 'ecom.<namespace>.<verb>'")
        verb = self.name.rsplit(".", 1)[1]
        is_write_verb = any(verb == v or verb.startswith(f"{v}_") for v in _WRITE_VERBS)
        if is_write_verb and self.read_or_write is not ReadOrWrite.write:
            raise ValueError(
                f"tool {self.name!r} uses a write verb but is declared read; "
                "a read tool must never mutate state (Runtime §6.1)"
            )
        if self.read_or_write is ReadOrWrite.write:
            # A write must be reconcilable and bound to a connection (I-06/I-07/I-08).
            if not self.required_connection_types:
                raise ValueError(f"write tool {self.name!r} must declare required_connection_types")
            if self.reconciliation_strategy is ReconciliationStrategy.none:
                raise ValueError(f"write tool {self.name!r} must declare a reconciliation_strategy")
        if self.store_scope_rule not in {"none", "optional", "required"}:
            raise ValueError(f"invalid store_scope_rule {self.store_scope_rule!r}")

    @property
    def schema_hash(self) -> str:
        """Deterministic hash over the wire-relevant shape of this tool.

        Changing name/version/either schema changes the hash; a hash mismatch fails an
        invocation before domain execution (Runtime §13.4).
        """
        payload = {
            "name": self.name,
            "version": self.version,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


@dataclass
class ToolCatalog:
    """Registry of canonical tool definitions plus a catalog compatibility hash."""

    version: str
    _tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, definition: ToolDefinition) -> ToolDefinition:
        if definition.name in self._tools:
            raise ValueError(f"duplicate tool registration: {definition.name!r}")
        self._tools[definition.name] = definition
        return definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def definitions(self, allowlist: frozenset[str] | None = None) -> list[ToolDefinition]:
        items = [self._tools[n] for n in self.names]
        if allowlist is not None:
            items = [d for d in items if d.name in allowlist]
        return items

    @property
    def compatibility_hash(self) -> str:
        """Hash over the catalog version and every tool's schema_hash.

        The adapter and MCP generators both read this catalog; a stable compatibility
        hash is the artifact the conformance suite pins so the two surfaces cannot drift.
        """
        payload = {
            "catalog_version": self.version,
            "tools": {d.name: d.schema_hash for d in self.definitions()},
        }
        digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


# --- The canonical v1 catalog ------------------------------------------------
# A03 seeds the read tools needed to prove the Slice 0 trace-correlation spike. Domain
# agents register their owned tools (orders, tickets, refunds, briefs) against this same
# catalog instance via their modules; they MUST NOT hand-maintain a second schema.

CATALOG = ToolCatalog(version="1.0.0")


def _obj(
    properties: dict[str, object],
    required: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


CATALOG.register(
    ToolDefinition(
        name="ecom.store.get",
        version="1.0.0",
        description="Read basic info about a connected store (name, domain, currency).",
        input_schema=_obj({"store_id": {"type": "string"}}, ["store_id"]),
        output_schema=_obj(
            {
                "store_id": {"type": "string"},
                "name": {"type": "string"},
                "domain": {"type": "string"},
                "currency": {"type": "string"},
            }
        ),
        read_or_write=ReadOrWrite.read,
        risk_class=RiskClass.none,
        store_scope_rule="required",
        minimum_trace_coverage=Coverage.verified,
    )
)

CATALOG.register(
    ToolDefinition(
        name="ecom.order.get",
        version="1.0.0",
        description="Read one order by id, including fulfillment/tracking summary (WISMO).",
        input_schema=_obj(
            {"store_id": {"type": "string"}, "order_id": {"type": "string"}},
            ["store_id", "order_id"],
        ),
        output_schema=_obj(
            {
                "order_id": {"type": "string"},
                "found": {"type": "boolean"},
                "name": {"type": "string"},
                "fulfillment_status": {"type": "string"},
            }
        ),
        read_or_write=ReadOrWrite.read,
        risk_class=RiskClass.none,
        store_scope_rule="required",
        sensitive_fields=("customer_email",),
        minimum_trace_coverage=Coverage.verified,
    )
)

CATALOG.register(
    ToolDefinition(
        name="ecom.order.search",
        version="1.0.0",
        description="Find orders by order name (e.g. '#1001') or customer email.",
        input_schema=_obj(
            {"store_id": {"type": "string"}, "query": {"type": "string"}},
            ["store_id", "query"],
        ),
        output_schema=_obj({"count": {"type": "integer"}, "orders": {"type": "array"}}),
        read_or_write=ReadOrWrite.read,
        risk_class=RiskClass.none,
        store_scope_rule="required",
        sensitive_fields=("customer_email",),
        minimum_trace_coverage=Coverage.verified,
    )
)

CATALOG.register(
    ToolDefinition(
        name="ecom.trace.search",
        version="1.0.0",
        description="Search Ecom-OS traces by entity, tool, status, actor, or date range.",
        input_schema=_obj(
            {
                "query": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            }
        ),
        output_schema=_obj({"count": {"type": "integer"}, "traces": {"type": "array"}}),
        read_or_write=ReadOrWrite.read,
        risk_class=RiskClass.none,
        store_scope_rule="none",
        minimum_trace_coverage=Coverage.verified,
    )
)
