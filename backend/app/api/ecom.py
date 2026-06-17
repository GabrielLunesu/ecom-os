"""Ecom-OS endpoints: connection status for the bootstrap gate + Settings.

Single-tenant (one brand) — guarded by user auth, no org switching (Build Spec §1).
Responses carry provider/status only; never secrets (Invariant 5).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import HTTPException

from app.api.deps import require_user_auth
from app.db.session import get_session
from app.services.connection_health import connections_status
from app.services.metrics import store_metrics
from app.services.stores import ensure_seed, list_stores
from app.services.vault import (
    ensure_seed_vault,
    get_document,
    list_documents,
    upsert_document,
)

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


class VaultDocOut(BaseModel):
    slug: str
    title: str
    tags: str
    body: str


class VaultDocSummary(BaseModel):
    slug: str
    title: str
    tags: str


class VaultDocIn(BaseModel):
    title: str
    tags: str = ""
    body: str = ""


@router.get("/vault", response_model=list[VaultDocSummary])
async def get_vault(session: AsyncSession = Depends(get_session)) -> list[VaultDocSummary]:
    """List vault documents (titles/tags) — the markdown the agents read."""
    brand = await ensure_seed(session)
    await ensure_seed_vault(session, brand)
    docs = await list_documents(session)
    return [VaultDocSummary.model_validate(d, from_attributes=True) for d in docs]


@router.get("/vault/{slug}", response_model=VaultDocOut)
async def get_vault_doc(
    slug: str, session: AsyncSession = Depends(get_session)
) -> VaultDocOut:
    doc = await get_document(session, slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    return VaultDocOut.model_validate(doc, from_attributes=True)


@router.put("/vault/{slug}", response_model=VaultDocOut)
async def put_vault_doc(
    slug: str, payload: VaultDocIn, session: AsyncSession = Depends(get_session)
) -> VaultDocOut:
    brand = await ensure_seed(session)
    doc = await upsert_document(
        session,
        brand=brand,
        slug=slug,
        title=payload.title,
        tags=payload.tags,
        body=payload.body,
    )
    return VaultDocOut.model_validate(doc, from_attributes=True)
