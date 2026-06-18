"""Generate adapter and MCP tool schemas from the one canonical catalog (Runtime §6.1).

Both surfaces are produced from the same ``ToolCatalog`` so they cannot drift. An optional
``allowlist`` selects the subset a given Hermes profile/MCP config may see — discovery of a
tool never implies business authorization (Runtime §2.4).
"""

from __future__ import annotations

from typing import Any

import mcp.types as mcp_types

from .catalog import CATALOG, ToolCatalog, ToolDefinition


def _meta(definition: ToolDefinition) -> dict[str, Any]:
    """Risk/version metadata carried alongside each generated tool."""
    return {
        "ecom_version": definition.version,
        "ecom_schema_hash": definition.schema_hash,
        "ecom_read_or_write": definition.read_or_write.value,
        "ecom_risk_class": definition.risk_class.value,
        "ecom_store_scope_rule": definition.store_scope_rule,
        "ecom_required_connection_types": list(definition.required_connection_types),
        "ecom_minimum_trace_coverage": definition.minimum_trace_coverage.value,
    }


def to_mcp_tools(
    catalog: ToolCatalog = CATALOG, *, allowlist: frozenset[str] | None = None
) -> list[mcp_types.Tool]:
    """Emit the MCP tool list (Runtime §2.4)."""
    tools: list[mcp_types.Tool] = []
    for definition in catalog.definitions(allowlist):
        tools.append(
            mcp_types.Tool(
                name=definition.name,
                description=definition.description,
                inputSchema=dict(definition.input_schema),
                outputSchema=dict(definition.output_schema),
                # mcp's Tool model aliases the metadata field as ``_meta``.
                **{"_meta": _meta(definition)},
            )
        )
    return tools


def to_adapter_registration(
    catalog: ToolCatalog = CATALOG, *, allowlist: frozenset[str] | None = None
) -> list[dict[str, Any]]:
    """Emit the Hermes-side adapter proxy registration schema (Runtime §2.3).

    The adapter is a thin proxy: it carries name/version/schema_hash/input_schema and risk
    metadata, never ecommerce logic or credentials.
    """
    registrations: list[dict[str, Any]] = []
    for definition in catalog.definitions(allowlist):
        registrations.append(
            {
                "name": definition.name,
                "version": definition.version,
                "schema_hash": definition.schema_hash,
                "description": definition.description,
                "input_schema": dict(definition.input_schema),
                "output_schema": dict(definition.output_schema),
                **_meta(definition),
            }
        )
    return registrations


def catalog_manifest(catalog: ToolCatalog = CATALOG) -> dict[str, Any]:
    """A compact manifest for the compatibility record (Runtime §3.1)."""
    return {
        "catalog_version": catalog.version,
        "compatibility_hash": catalog.compatibility_hash,
        "tools": {d.name: d.schema_hash for d in catalog.definitions()},
    }
