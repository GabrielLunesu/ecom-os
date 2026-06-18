"""Evidence-backed read tools over the normalized commerce model.

These are the read surfaces an agent/UI uses to answer "where is my order" with
provenance. Every tool is read-only (``read_or_write="read"``), enforces store scope,
and returns the runtime result envelope (RUNTIME §6.3): ``ok``/``status``/``data``/
``evidence``/``freshness``/``coverage``. Tools never mutate state and never return a
secret. The :data:`READ_TOOL_MANIFEST` is what A04 registers into A03's catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.connectors.ports import ReadResult
from app.connectors.read_repository import CommerceReadRepository


@dataclass(frozen=True)
class ReadToolSpec:
    name: str
    description: str
    required_connection_types: tuple[str, ...]
    store_scope_rule: str
    minimum_trace_coverage: str = "imported"
    read_or_write: str = "read"
    supports_simulation: bool = True


READ_TOOL_MANIFEST: tuple[ReadToolSpec, ...] = (
    ReadToolSpec(
        "ecom.store.list",
        "List stores and their connection health.",
        (),
        "all_stores",
        minimum_trace_coverage="verified",
    ),
    ReadToolSpec(
        "ecom.order.get",
        "Get one order by id/number with tracking + evidence.",
        ("store",),
        "single_store",
    ),
    ReadToolSpec(
        "ecom.order.search",
        "Find a customer's orders by email.",
        ("store",),
        "single_store",
    ),
    ReadToolSpec(
        "ecom.customer.get",
        "Get one customer by email/id with evidence.",
        ("store",),
        "single_store",
    ),
)


def _envelope(result: ReadResult[Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "ok": True,
            "status": "completed",
            "data": None,
            "freshness": {"as_of": None, "status": "partial"},
            "coverage": "unknown",
            "evidence": [],
            "warnings": ["not_found"],
        }
    body = result.to_envelope()
    status = "degraded" if result.freshness.status in ("stale", "partial") else "completed"
    return {"ok": True, "status": status, **body}


class CommerceReadTools:
    """Bound read-tool handlers for one repository/session."""

    def __init__(self, repo: CommerceReadRepository) -> None:
        self._repo = repo

    async def store_list(self) -> dict[str, Any]:
        return _envelope(await self._repo.list_stores())

    async def order_get(self, store_id: UUID, identifier: str) -> dict[str, Any]:
        return _envelope(await self._repo.get_order(store_id, identifier))

    async def order_search(self, store_id: UUID, email: str) -> dict[str, Any]:
        return _envelope(await self._repo.find_orders_by_customer(store_id, email))

    async def customer_get(self, store_id: UUID, identifier: str) -> dict[str, Any]:
        return _envelope(await self._repo.get_customer(store_id, identifier))
