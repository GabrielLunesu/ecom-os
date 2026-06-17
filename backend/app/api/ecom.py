"""Ecom-OS endpoints: connection status for the bootstrap gate + Settings.

Single-tenant (one brand) — guarded by user auth, no org switching (Build Spec §1).
Responses carry provider/status only; never secrets (Invariant 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_user_auth
from app.services.connection_health import connections_status

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
