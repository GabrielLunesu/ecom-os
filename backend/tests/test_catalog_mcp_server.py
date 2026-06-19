"""Tests for the catalog-generated MCP server (Runtime Spec §6.1, §2.4).

Proves the generation path: exposed tools + schemas come from the one catalog, an allowlist
filters them, calls validate against the catalog before dispatch, and a handler for a tool
outside the catalog is rejected.
"""

from __future__ import annotations

import pytest

from app.mcp_server.catalog_server import (
    build_catalog_handlers,
    build_catalog_server,
)
from app.tools.catalog import CATALOG
from app.tools.envelope import SchemaMismatchError
from app.tools.generators import to_mcp_tools


async def _order_handler(arguments: dict[str, object]) -> dict[str, object]:
    return {"order_id": arguments["order_id"], "found": True, "name": "#1001"}


def test_server_lists_catalog_tools() -> None:
    allow = frozenset({"ecom.order.get"})
    build_catalog_server({"ecom.order.get": _order_handler}, allowlist=allow)
    tools = to_mcp_tools(CATALOG, allowlist=allow)
    assert {t.name for t in tools} == {"ecom.order.get"}
    assert tools[0].meta is not None
    assert tools[0].meta["ecom_schema_hash"].startswith("sha256:")


def test_handler_outside_catalog_rejected() -> None:
    with pytest.raises(ValueError, match="not an allowed catalog tool"):
        build_catalog_handlers({"ecom.not_a_tool.get": _order_handler})


@pytest.mark.asyncio
async def test_validated_handler_runs_on_good_args() -> None:
    handlers = build_catalog_handlers(
        {"ecom.order.get": _order_handler}, allowlist=frozenset({"ecom.order.get"})
    )
    out = await handlers["ecom.order.get"]({"store_id": "st_1", "order_id": "ord_1"})
    assert out["name"] == "#1001"


@pytest.mark.asyncio
async def test_validated_handler_rejects_bad_args_before_dispatch() -> None:
    calls = {"n": 0}

    async def spy(arguments: dict[str, object]) -> dict[str, object]:
        calls["n"] += 1
        return {}

    handlers = build_catalog_handlers(
        {"ecom.order.get": spy}, allowlist=frozenset({"ecom.order.get"})
    )
    with pytest.raises(SchemaMismatchError):
        await handlers["ecom.order.get"]({"order_id": "ord_1"})  # missing store_id
    assert calls["n"] == 0  # handler never ran
