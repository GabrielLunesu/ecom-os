"""Ecom-OS endpoints: connection status for the bootstrap gate + Settings.

Single-tenant (one brand) — guarded by user auth, no org switching (Build Spec §1).
Responses carry provider/status only; never secrets (Invariant 5).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import require_user_auth
from app.db.session import get_session
from app.services.connection_health import connections_status
from app.services.metrics import store_metrics
from app.services.stores import ensure_seed, list_stores

router = APIRouter(prefix="/ecom", tags=["ecom"], dependencies=[Depends(require_user_auth)])


class ProviderHealthOut(BaseModel):
    provider: str
    connected: bool
    detail: str


class ConnectionsOut(BaseModel):
    ready: bool
    providers: list[ProviderHealthOut]


@router.get("/connections", response_model=ConnectionsOut)
async def get_connections() -> ConnectionsOut:
    """Live connection health for Shopify + the support inbox (Build Spec §1.5)."""
    status = await connections_status()
    return ConnectionsOut.model_validate(status)


class StoreOut(BaseModel):
    id: UUID
    name: str
    domain: str
    provider: str
    status: str


@router.get("/stores", response_model=list[StoreOut])
async def get_stores(session: AsyncSession = Depends(get_session)) -> list[StoreOut]:
    """List the brand's stores (connection refs only — never secrets)."""
    await ensure_seed(session)
    stores = await list_stores(session)
    return [StoreOut.model_validate(s, from_attributes=True) for s in stores]


@router.get("/metrics")
async def get_metrics(
    store: str = "all",
    days: int = 30,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """KPIs for a store or the aggregate (Build Spec §7.1). Order-derived; session
    metrics return null with a reason (no read_reports scope)."""
    await ensure_seed(session)
    days = max(1, min(days, 365))
    return await store_metrics(session, store_id=store, days=days)
