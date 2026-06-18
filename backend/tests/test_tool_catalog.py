"""Tests for the canonical tool catalog and its generators (Runtime Spec §6).

Proves the single-catalog guarantee: adapter and MCP schemas are generated from one
source, schema hashes are deterministic, the read/write classification is enforced, and an
invocation with a stale version/hash fails before domain execution (Runtime §13.4).
"""

from __future__ import annotations

import re

import pytest

from app.tools.catalog import (
    CATALOG,
    Coverage,
    ReadOrWrite,
    ReconciliationStrategy,
    RiskClass,
    ToolCatalog,
    ToolDefinition,
)
from app.tools.envelope import (
    InvocationContext,
    SchemaMismatchError,
    ToolInvocation,
    UnknownToolError,
    redact,
    validate_invocation,
)
from app.tools.generators import (
    catalog_manifest,
    to_adapter_registration,
    to_mcp_tools,
)

FORBIDDEN = re.compile(r"refund|cancel|delete|void", re.IGNORECASE)


def _read_def(name: str = "ecom.order.get") -> ToolDefinition:
    return CATALOG.get(name)  # type: ignore[return-value]


# --- definition validation ---------------------------------------------------
def test_name_must_be_namespaced() -> None:
    with pytest.raises(ValueError, match="ecom.<namespace>.<verb>"):
        ToolDefinition(
            name="order_get",
            version="1.0.0",
            description="x",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_or_write=ReadOrWrite.read,
            risk_class=RiskClass.none,
        )


def test_read_tool_with_write_verb_is_rejected() -> None:
    """A read tool named with a write verb is the exact anti-pattern §6.1 forbids."""
    with pytest.raises(ValueError, match="write verb but is declared read"):
        ToolDefinition(
            name="ecom.order.update",
            version="1.0.0",
            description="sneaky",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_or_write=ReadOrWrite.read,
            risk_class=RiskClass.low,
        )


def test_write_tool_requires_connection_and_reconciliation() -> None:
    with pytest.raises(ValueError, match="required_connection_types"):
        ToolDefinition(
            name="ecom.refund.execute",
            version="1.0.0",
            description="refund",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_or_write=ReadOrWrite.write,
            risk_class=RiskClass.critical,
        )

    with pytest.raises(ValueError, match="reconciliation_strategy"):
        ToolDefinition(
            name="ecom.refund.execute",
            version="1.0.0",
            description="refund",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            read_or_write=ReadOrWrite.write,
            risk_class=RiskClass.critical,
            required_connection_types=("shopify",),
        )


def test_valid_write_tool_constructs() -> None:
    tool = ToolDefinition(
        name="ecom.refund.execute",
        version="1.0.0",
        description="Execute a refund against the bound connection.",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        read_or_write=ReadOrWrite.write,
        risk_class=RiskClass.critical,
        required_connection_types=("shopify",),
        supports_idempotency=True,
        reconciliation_strategy=ReconciliationStrategy.provider_lookup,
    )
    assert tool.read_or_write is ReadOrWrite.write


# --- hashing -----------------------------------------------------------------
def test_schema_hash_is_deterministic_and_prefixed() -> None:
    d = _read_def()
    assert d.schema_hash == d.schema_hash
    assert d.schema_hash.startswith("sha256:")


def test_schema_hash_changes_with_version() -> None:
    d = _read_def()
    bumped = ToolDefinition(
        name=d.name,
        version="1.0.1",
        description=d.description,
        input_schema=d.input_schema,
        output_schema=d.output_schema,
        read_or_write=d.read_or_write,
        risk_class=d.risk_class,
        store_scope_rule=d.store_scope_rule,
    )
    assert bumped.schema_hash != d.schema_hash


def test_catalog_compatibility_hash_stable() -> None:
    assert CATALOG.compatibility_hash == CATALOG.compatibility_hash
    assert CATALOG.compatibility_hash.startswith("sha256:")


# --- single-catalog generation -----------------------------------------------
def test_adapter_and_mcp_generated_from_same_catalog() -> None:
    mcp_tools = to_mcp_tools()
    adapter = to_adapter_registration()
    mcp_names = {t.name for t in mcp_tools}
    adapter_names = {r["name"] for r in adapter}
    assert mcp_names == adapter_names == set(CATALOG.names)
    # Hashes match across surfaces (no drift).
    adapter_hashes = {r["name"]: r["schema_hash"] for r in adapter}
    for tool in mcp_tools:
        assert tool.meta is not None
        assert tool.meta["ecom_schema_hash"] == adapter_hashes[tool.name]


def test_allowlist_filters_both_surfaces() -> None:
    allow = frozenset({"ecom.order.get"})
    assert {t.name for t in to_mcp_tools(allowlist=allow)} == allow
    assert {r["name"] for r in to_adapter_registration(allowlist=allow)} == allow


def test_manifest_matches_catalog() -> None:
    manifest = catalog_manifest()
    assert manifest["compatibility_hash"] == CATALOG.compatibility_hash
    assert set(manifest["tools"]) == set(CATALOG.names)


def test_no_forbidden_tool_in_default_read_catalog() -> None:
    # The seeded A03 catalog ships read tools only; none is a refund/cancel/etc.
    for name in CATALOG.names:
        assert not FORBIDDEN.search(name), f"unexpected write tool seeded: {name}"


# --- invocation validation (fail before execution) ---------------------------
def _invocation(**overrides: object) -> ToolInvocation:
    d = _read_def()
    base = {
        "invocation_id": "inv_1",
        "tool_name": d.name,
        "tool_version": d.version,
        "schema_hash": d.schema_hash,
        "arguments": {"store_id": "st_1", "order_id": "ord_1"},
        "context": InvocationContext(trace_id="trc_1"),
    }
    base.update(overrides)
    return ToolInvocation(**base)  # type: ignore[arg-type]


def test_valid_invocation_resolves() -> None:
    definition = validate_invocation(CATALOG, _invocation())
    assert definition.name == "ecom.order.get"


def test_unknown_tool_rejected() -> None:
    with pytest.raises(UnknownToolError):
        validate_invocation(CATALOG, _invocation(tool_name="ecom.nope.get"))


def test_version_mismatch_rejected() -> None:
    with pytest.raises(SchemaMismatchError, match="version"):
        validate_invocation(CATALOG, _invocation(tool_version="9.9.9"))


def test_schema_hash_mismatch_rejected() -> None:
    with pytest.raises(SchemaMismatchError, match="schema hash mismatch"):
        validate_invocation(CATALOG, _invocation(schema_hash="sha256:deadbeef"))


def test_missing_required_argument_rejected() -> None:
    with pytest.raises(SchemaMismatchError, match="missing required"):
        validate_invocation(CATALOG, _invocation(arguments={"store_id": "st_1"}))


def test_unknown_argument_rejected() -> None:
    with pytest.raises(SchemaMismatchError, match="unknown arguments"):
        validate_invocation(
            CATALOG,
            _invocation(
                arguments={"store_id": "st_1", "order_id": "o", "evil": "x"}
            ),
        )


# --- redaction ---------------------------------------------------------------
def test_redact_masks_sensitive_fields() -> None:
    d = _read_def()  # declares customer_email sensitive
    masked = redact(d, {"order_id": "o1", "customer_email": "a@b.com"})
    assert masked["customer_email"] == "[redacted]"
    assert masked["order_id"] == "o1"


def test_isolated_catalog_registration() -> None:
    cat = ToolCatalog(version="9.9.9")
    cat.register(_read_def())
    with pytest.raises(ValueError, match="duplicate"):
        cat.register(_read_def())
    assert cat.names == ("ecom.order.get",)
