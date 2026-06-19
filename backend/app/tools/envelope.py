"""Normalized tool invocation/result envelopes (Runtime Spec §6.2 / §6.3).

Adapter and MCP transports both normalize into ``ToolInvocation``; every tool returns a
``ToolResult``. ``validate_invocation`` enforces the schema-hash/version contract *before*
domain execution (Runtime §13.4): a mismatch fails fast and never "best-effort"
reinterprets a money-touching argument.

Identity and scope are resolved server-side from authenticated context; client-supplied
context fields are asserted metadata only. Missing Hermes fields stay ``None`` rather than
being fabricated (Runtime §6.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .catalog import Coverage, ToolCatalog, ToolDefinition


class ToolStatus(str, Enum):
    completed = "completed"
    proposed = "proposed"
    awaiting_approval = "awaiting_approval"
    queued = "queued"
    degraded = "degraded"
    failed = "failed"


class UnknownToolError(ValueError):
    """The invoked tool name is not in the catalog."""


class SchemaMismatchError(ValueError):
    """Tool version or schema hash does not match the catalog (Runtime §13.4)."""


@dataclass(frozen=True)
class InvocationContext:
    """Hermes-supplied + Ecom-OS-resolved correlation context (Runtime §6.2).

    Every field is optional: a transport that cannot supply one leaves it ``None``.
    Effective identity/store/connection are resolved server-side, not trusted from here.
    """

    trace_id: str | None = None
    run_id: str | None = None
    hermes_profile_id: str | None = None
    hermes_session_id: str | None = None
    hermes_run_id: str | None = None
    hermes_tool_call_id: str | None = None
    source_platform: str | None = None
    ecom_user_id: str | None = None
    channel_identity_id: str | None = None
    store_id: str | None = None
    connection_id: str | None = None


@dataclass(frozen=True)
class ToolInvocation:
    """The normalized inbound call (Runtime §6.2)."""

    invocation_id: str
    tool_name: str
    tool_version: str
    schema_hash: str
    arguments: dict[str, object]
    context: InvocationContext = field(default_factory=InvocationContext)


@dataclass(frozen=True)
class Freshness:
    as_of: str | None = None
    status: str = "current"  # "current" | "stale" | "partial"


@dataclass(frozen=True)
class ToolResult:
    """The machine-readable result envelope (Runtime §6.3)."""

    ok: bool
    status: ToolStatus
    invocation_id: str
    trace_id: str | None = None
    action_id: str | None = None
    approval_id: str | None = None
    data: dict[str, object] = field(default_factory=dict)
    evidence: tuple[dict[str, str], ...] = ()
    freshness: Freshness | None = None
    warnings: tuple[str, ...] = ()
    error: dict[str, str] | None = None
    coverage: Coverage = Coverage.verified


def _validate_arguments(definition: ToolDefinition, arguments: dict[str, object]) -> None:
    """Lightweight required/unknown-key validation from the catalog input schema.

    This is the server validation model generated from the canonical catalog. It is not a
    full JSON-Schema engine; it enforces required keys and (when the schema forbids extras)
    rejects unknown keys, which is what protects against malformed/forged arguments before
    domain execution.
    """
    schema = definition.input_schema
    required_raw = schema.get("required", [])
    properties_raw = schema.get("properties", {})
    required: set[str] = set(required_raw) if isinstance(required_raw, list) else set()
    properties: dict[str, object] = properties_raw if isinstance(properties_raw, dict) else {}
    missing = required - set(arguments)
    if missing:
        raise SchemaMismatchError(
            f"{definition.name}: missing required arguments {sorted(missing)}"
        )
    if schema.get("additionalProperties") is False:
        unknown = set(arguments) - set(properties)
        if unknown:
            raise SchemaMismatchError(f"{definition.name}: unknown arguments {sorted(unknown)}")


def validate_invocation(catalog: ToolCatalog, invocation: ToolInvocation) -> ToolDefinition:
    """Resolve and validate an invocation against the catalog before execution.

    Raises ``UnknownToolError`` for an unregistered tool, ``SchemaMismatchError`` for a
    version/hash/argument mismatch. Returns the matched ``ToolDefinition``.
    """
    definition = catalog.get(invocation.tool_name)
    if definition is None:
        raise UnknownToolError(f"unknown tool: {invocation.tool_name!r}")
    if invocation.tool_version != definition.version:
        raise SchemaMismatchError(
            f"{invocation.tool_name}: version {invocation.tool_version!r} != "
            f"catalog {definition.version!r}"
        )
    if invocation.schema_hash != definition.schema_hash:
        raise SchemaMismatchError(
            f"{invocation.tool_name}: schema hash mismatch "
            f"(got {invocation.schema_hash}, catalog {definition.schema_hash})"
        )
    _validate_arguments(definition, invocation.arguments)
    return definition


def redact(definition: ToolDefinition, data: dict[str, object]) -> dict[str, object]:
    """Redact declared sensitive fields from a result payload (Runtime §14).

    A tool never returns a plaintext secret; declared ``sensitive_fields`` are masked
    before the payload leaves the handler.
    """
    if not definition.sensitive_fields:
        return data
    masked = dict(data)
    for key in definition.sensitive_fields:
        if key in masked and masked[key] is not None:
            masked[key] = "[redacted]"
    return masked
