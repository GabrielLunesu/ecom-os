"""Build an MCP server whose tools are generated from the canonical catalog (Runtime §6.1).

This is the migration target for the hand-maintained `server.py`: instead of a hand-written
`TOOLS` list, the exposed tools and their schemas come from one `ToolCatalog`, and every call
is validated against that catalog before dispatch (§13.4). Domain agents register their owned
tool definitions into the catalog; A03 owns this generation mechanism.

The live CS server keeps its current A05-owned tool names until A05 registers them into the
catalog (registration contract) — this module proves the generation path end-to-end without
disturbing that contract.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import mcp.types as mcp_types
from mcp.server.lowlevel import Server

from app.core.logging import get_logger
from app.tools.catalog import CATALOG, ToolCatalog
from app.tools.envelope import SchemaMismatchError, validate_invocation
from app.tools.envelope import ToolInvocation
from app.tools.generators import to_mcp_tools

logger = get_logger(__name__)

# A catalog handler receives validated arguments and returns a JSON-able payload.
CatalogHandler = Callable[[dict[str, Any]], Awaitable[Any]]


def build_catalog_handlers(
    handlers: dict[str, CatalogHandler],
    *,
    catalog: ToolCatalog = CATALOG,
    allowlist: frozenset[str] | None = None,
) -> dict[str, CatalogHandler]:
    """Wrap raw handlers with catalog argument validation before dispatch.

    Each wrapped handler builds a ``ToolInvocation`` at the catalog's current version/hash and
    runs ``validate_invocation`` so unknown args / schema drift fail before the handler runs.
    """
    allowed = {
        d.name
        for d in catalog.definitions(allowlist)
    }
    wrapped: dict[str, CatalogHandler] = {}
    for name, handler in handlers.items():
        if name not in allowed:
            raise ValueError(f"handler {name!r} is not an allowed catalog tool")

        definition = catalog.get(name)
        assert definition is not None

        async def _validated(
            arguments: dict[str, Any],
            _handler: CatalogHandler = handler,
            _name: str = name,
        ) -> Any:
            invocation = ToolInvocation(
                invocation_id=f"mcp_{_name}",
                tool_name=_name,
                tool_version=definition.version,
                schema_hash=definition.schema_hash,
                arguments=arguments,
            )
            validate_invocation(catalog, invocation)  # raises on mismatch (§13.4)
            return await _handler(arguments)

        wrapped[name] = _validated
    return wrapped


def build_catalog_server(
    handlers: dict[str, CatalogHandler],
    *,
    catalog: ToolCatalog = CATALOG,
    allowlist: frozenset[str] | None = None,
    server_name: str = "mcp-ecom-os-catalog",
) -> Server:
    """Construct a low-level MCP server exposing catalog-generated tools."""
    tools = to_mcp_tools(catalog, allowlist=allowlist)
    validated = build_catalog_handlers(handlers, catalog=catalog, allowlist=allowlist)
    server: Server = Server(server_name)

    @server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def _list_tools() -> list[mcp_types.Tool]:
        return tools

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = validated.get(name)
        if handler is None:
            raise SchemaMismatchError(f"unknown or unauthorized tool: {name!r}")
        logger.info("mcp.catalog.tool.call", extra={"tool": name})
        result = await handler(arguments or {})
        return {"result": result}

    return server
