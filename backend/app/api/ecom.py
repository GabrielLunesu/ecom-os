"""Ecom-OS endpoints: connection status for the bootstrap gate + Settings.

Single-tenant (one brand) — guarded by user auth, no org switching (Build Spec §1).
Responses carry provider/status only; never secrets (Invariant 5).
"""

from __future__ import annotations

from datetime import datetime
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
from app.services.tickets import (
    get_ticket,
    ingest_inbox,
    list_tickets,
    ticket_evidence,
    ticket_messages,
)
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


# --- Tickets (CS) ---
class TicketOut(BaseModel):
    id: UUID
    subject: str
    customer_email: str
    customer_name: str
    status: str
    channel: str
    created_at: datetime
    updated_at: datetime


class TicketMessageOut(BaseModel):
    direction: str
    author: str
    body: str
    untrusted: bool
    created_at: datetime


class TicketEvidenceOut(BaseModel):
    kind: str
    summary: str
    created_at: datetime


class TicketDetailOut(TicketOut):
    messages: list[TicketMessageOut]
    evidence: list[TicketEvidenceOut]


@router.get("/tickets", response_model=list[TicketOut])
async def get_tickets(session: AsyncSession = Depends(get_session)) -> list[TicketOut]:
    tickets = await list_tickets(session)
    return [TicketOut.model_validate(t, from_attributes=True) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
async def get_ticket_detail(
    ticket_id: UUID, session: AsyncSession = Depends(get_session)
) -> TicketDetailOut:
    ticket = await get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    msgs = await ticket_messages(session, ticket_id)
    ev = await ticket_evidence(session, ticket_id)
    return TicketDetailOut(
        **TicketOut.model_validate(ticket, from_attributes=True).model_dump(),
        messages=[TicketMessageOut.model_validate(m, from_attributes=True) for m in msgs],
        evidence=[TicketEvidenceOut.model_validate(e, from_attributes=True) for e in ev],
    )


@router.post("/tickets/ingest")
async def post_ingest(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Pull unread inbound mail and create tickets (Build Spec §7, §9a step 2)."""
    brand = await ensure_seed(session)
    created = await ingest_inbox(session, brand)
    return {"ingested": len(created), "ticket_ids": [str(t.id) for t in created]}


@router.post("/cs/run")
async def post_cs_run(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Run the CS loop: ingest mail + autonomously handle actionable tickets.

    Gated on the §1.5 health check; the CS agent has read + discount tools only
    (Invariant 2). This is the engine behind the WISMO acceptance test (§9a)."""
    from app.services.cs_loop import run_cs_loop

    return await run_cs_loop(session)


# --- Refunds (separate, approval-gated path — Invariant 2) ---
class RefundOut(BaseModel):
    id: UUID
    order_name: str
    amount: float
    currency: str
    reason: str
    status: str
    requested_by: str
    approved_by: str
    error: str


class RefundIn(BaseModel):
    order_id: str
    order_name: str = ""
    amount: float
    currency: str = "USD"
    reason: str = ""
    ticket_id: UUID | None = None


@router.get("/refunds", response_model=list[RefundOut])
async def get_refunds(session: AsyncSession = Depends(get_session)) -> list[RefundOut]:
    from app.services.refunds import list_refunds

    return [RefundOut.model_validate(r, from_attributes=True) for r in await list_refunds(session)]


@router.post("/refunds", response_model=RefundOut)
async def post_refund(payload: RefundIn, session: AsyncSession = Depends(get_session)) -> RefundOut:
    from app.services.refunds import create_refund_request

    brand = await ensure_seed(session)
    req = await create_refund_request(
        session,
        brand=brand,
        order_id=payload.order_id,
        order_name=payload.order_name,
        amount=payload.amount,
        currency=payload.currency,
        reason=payload.reason,
        requested_by="operator",
        ticket_id=payload.ticket_id,
    )
    return RefundOut.model_validate(req, from_attributes=True)


@router.post("/refunds/{refund_id}/approve", response_model=RefundOut)
async def approve_refund_ep(
    refund_id: UUID, session: AsyncSession = Depends(get_session)
) -> RefundOut:
    """Approve + execute via the separately-scoped RefundExecutor (Invariant 2)."""
    from app.services.connectors.refunds import RefundExecutor
    from app.services.refunds import approve_refund

    req = await approve_refund(session, refund_id, "operator", RefundExecutor.from_env())
    return RefundOut.model_validate(req, from_attributes=True)


@router.post("/refunds/{refund_id}/reject", response_model=RefundOut)
async def reject_refund_ep(
    refund_id: UUID, session: AsyncSession = Depends(get_session)
) -> RefundOut:
    from app.services.refunds import reject_refund

    req = await reject_refund(session, refund_id, "operator")
    return RefundOut.model_validate(req, from_attributes=True)
