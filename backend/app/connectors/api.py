"""Commerce read API (Orders / Customers / Stores / connection settings).

This router is the backend behind the A04-owned ``/orders`` and ``/customers`` UI
routes. It is exported here (A04-owned) and registered centrally by A01/A09 behind
the standard auth dependency (see INTERFACES.md IR-A02-/IR-A04-02) — A04 does not edit
``main.py``. Every response renders an operational state: ``ok`` data with explicit
freshness/coverage/evidence, a ``degraded`` status when stale/partial, and 404 for a
missing resource. Routes contain no connector or policy logic (AGENTS.md §10).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connectors.read_repository import CommerceReadRepository
from app.connectors.tools import CommerceReadTools
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/ecom/commerce", tags=["commerce"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _tools(session: AsyncSession) -> CommerceReadTools:
    return CommerceReadTools(CommerceReadRepository(session))


@router.get("/stores")
async def list_stores(session: SessionDep) -> dict[str, object]:
    return await _tools(session).store_list()


@router.get("/stores/{store_id}/orders/{identifier}")
async def get_order(store_id: UUID, identifier: str, session: SessionDep) -> dict[str, object]:
    result = await _tools(session).order_get(store_id, identifier)
    if result["data"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    return result


@router.get("/stores/{store_id}/orders")
async def search_orders(store_id: UUID, email: str, session: SessionDep) -> dict[str, object]:
    return await _tools(session).order_search(store_id, email)


@router.get("/stores/{store_id}/customers/{identifier}")
async def get_customer(store_id: UUID, identifier: str, session: SessionDep) -> dict[str, object]:
    result = await _tools(session).customer_get(store_id, identifier)
    if result["data"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer_not_found")
    return result
