"""Ecom-OS endpoints: connection status for the bootstrap gate + Settings.

Single-tenant (one brand) — guarded by user auth, no org switching (Build Spec §1).
Responses carry provider/status only; never secrets (Invariant 5).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import require_user_auth
from app.db.session import get_session
from app.services.connection_health import connections_status
from app.services.metrics import store_metrics
from app.services.secret_store import list_handles, set_secret, unset_secret
from app.services.stores import add_store, ensure_seed, list_stores, remove_store
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
async def get_connections(session: AsyncSession = Depends(get_session)) -> ConnectionsOut:
    """Live connection health for Shopify + the support inbox (Build Spec §1.5)."""
    await ensure_seed(session)
    status = await connections_status(session)
    return ConnectionsOut.model_validate(status)


class StoreOut(BaseModel):
    id: UUID
    name: str
    domain: str
    provider: str
    status: str
    public_url: str = ""
    support_email: str = ""
    support_name: str = ""
    tracking_url: str = ""
    facts: str = ""


class StoreProfileIn(BaseModel):
    name: str = ""
    public_url: str = ""
    support_email: str = ""
    support_name: str = ""
    tracking_url: str = ""
    facts: str = ""


@router.get("/stores", response_model=list[StoreOut])
async def get_stores(session: AsyncSession = Depends(get_session)) -> list[StoreOut]:
    """List the brand's stores (connection refs only — never secrets)."""
    await ensure_seed(session)
    stores = await list_stores(session)
    return [StoreOut.model_validate(s, from_attributes=True) for s in stores]


# --- Settings: dashboard-managed encrypted secrets (Invariant 5) ---
class SecretHandleOut(BaseModel):
    handle: str
    set: bool


class SecretIn(BaseModel):
    value: str


@router.get("/settings/secrets", response_model=list[SecretHandleOut])
async def get_secrets(session: AsyncSession = Depends(get_session)) -> list[SecretHandleOut]:
    """List which secret handles are set — values are NEVER returned (Invariant 5)."""
    return [SecretHandleOut(handle=h, set=True) for h in await list_handles(session)]


@router.put("/settings/secrets/{handle}", response_model=SecretHandleOut)
async def put_secret(
    handle: str, payload: SecretIn, session: AsyncSession = Depends(get_session)
) -> SecretHandleOut:
    """Set an encrypted secret by handle. The value is never logged or returned."""
    brand = await ensure_seed(session)
    await set_secret(session, brand, handle, payload.value)
    return SecretHandleOut(handle=handle, set=True)


@router.delete("/settings/secrets/{handle}", response_model=SecretHandleOut)
async def delete_secret(
    handle: str, session: AsyncSession = Depends(get_session)
) -> SecretHandleOut:
    brand = await ensure_seed(session)
    await unset_secret(session, brand, handle)
    return SecretHandleOut(handle=handle, set=False)


# --- Stores: multi-store management ---
class StoreCreateIn(BaseModel):
    domain: str
    name: str = ""


@router.post("/stores", response_model=StoreOut)
async def post_store(
    payload: StoreCreateIn, session: AsyncSession = Depends(get_session)
) -> StoreOut:
    """Add a store (connection ref only — token is set separately)."""
    brand = await ensure_seed(session)
    store = await add_store(session, brand, domain=payload.domain, name=payload.name)
    return StoreOut.model_validate(store, from_attributes=True)


@router.put("/stores/{store_id}/profile", response_model=StoreOut)
async def put_store_profile(
    store_id: UUID, payload: StoreProfileIn, session: AsyncSession = Depends(get_session)
) -> StoreOut:
    """Set the store profile (real facts the agent uses — never hallucinates)."""
    from app.services.stores import update_store_profile

    store = await update_store_profile(
        session,
        store_id,
        name=payload.name,
        public_url=payload.public_url,
        support_email=payload.support_email,
        support_name=payload.support_name,
        tracking_url=payload.tracking_url,
        facts=payload.facts,
    )
    if store is None:
        raise HTTPException(status_code=404, detail="store not found")
    return StoreOut.model_validate(store, from_attributes=True)


class ShopifyCredsIn(BaseModel):
    client_id: str
    client_secret: str


@router.put("/stores/{store_id}/shopify-credentials", response_model=StoreOut)
async def put_shopify_credentials(
    store_id: UUID, payload: ShopifyCredsIn, session: AsyncSession = Depends(get_session)
) -> StoreOut:
    """Connect a store with its app's client id + secret. The app mints the Admin
    API token via the client-credentials grant (no browser) and refreshes it. The
    creds are stored encrypted (write-only); the token is never persisted."""
    from app.models.brand import Store
    from app.services.connectors.shopify_token import fetch_client_credentials_token

    brand = await ensure_seed(session)
    store = await session.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="store not found")
    # Validate by minting a token now; fail clearly if the creds/store don't qualify.
    try:
        await fetch_client_credentials_token(store.domain, payload.client_id, payload.client_secret)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail=f"could not connect store ({type(exc).__name__}); check the client id/secret "
            "and that the app is installed on this store",
        ) from exc
    await set_secret(session, brand, f"SHOPIFY_CLIENT_ID:{store.domain}", payload.client_id)
    await set_secret(session, brand, f"SHOPIFY_CLIENT_SECRET:{store.domain}", payload.client_secret)
    store.status = "connected"
    session.add(store)
    await session.commit()
    await session.refresh(store)
    return StoreOut.model_validate(store, from_attributes=True)


@router.put("/stores/{store_id}/token", response_model=StoreOut)
async def put_store_token(
    store_id: UUID, payload: SecretIn, session: AsyncSession = Depends(get_session)
) -> StoreOut:
    """Set a store's Shopify token directly (encrypted) and mark it connected.

    Most users instead set client id/secret via /shopify-credentials and the app
    mints the token itself; this is the manual fallback for a static token."""
    from app.models.brand import Store

    brand = await ensure_seed(session)
    store = await session.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="store not found")
    await set_secret(session, brand, f"SHOPIFY_ACCESS_TOKEN:{store.domain}", payload.value)
    store.status = "connected"
    session.add(store)
    await session.commit()
    await session.refresh(store)
    return StoreOut.model_validate(store, from_attributes=True)


@router.delete("/stores/{store_id}")
async def delete_store(
    store_id: UUID, session: AsyncSession = Depends(get_session)
) -> dict[str, bool]:
    removed = await remove_store(session, store_id)
    if not removed:
        raise HTTPException(status_code=404, detail="store not found")
    return {"removed": True}


@router.get("/version")
async def get_version() -> dict[str, str]:
    """Backend version + short git commit (best-effort; never crashes)."""
    import subprocess
    from pathlib import Path

    version_file = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        version = "dev"
    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
            or "unknown"
        )
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    return {"version": version, "commit": commit}


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
async def get_vault_doc(slug: str, session: AsyncSession = Depends(get_session)) -> VaultDocOut:
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


# --- Realtime (instant handling via the inbound-email webhook) ---
def _realtime_webhook_url() -> str:
    from app.api.ecom_webhooks import webhook_secret
    from app.core.config import settings

    base = settings.base_url.rstrip("/")
    return f"{base}/api/v1/ecom/webhooks/email?token={webhook_secret()}"


@router.get("/realtime")
async def get_realtime() -> dict[str, object]:
    """Realtime status + the webhook URL to set as Composio's project webhook."""
    from app.services.realtime import realtime_status

    status = await realtime_status()
    return {**status, "webhook_url": _realtime_webhook_url()}


@router.post("/realtime/enable")
async def post_realtime_enable() -> dict[str, object]:
    """Enable the new-email trigger so the loop runs the instant mail arrives."""
    from app.services.realtime import enable_email_trigger

    result = await enable_email_trigger()
    return {**result, "webhook_url": _realtime_webhook_url()}


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


# --- Agents (templates + config) ---
class AgentOut(BaseModel):
    id: UUID
    template: str
    name: str
    voice: str
    sops: str
    allowed_tools: list[str] | None
    schedule: str
    enabled: bool


class AgentIn(BaseModel):
    voice: str
    sops: str
    schedule: str
    enabled: bool


class TaskOut(BaseModel):
    id: UUID
    title: str
    assignee: str
    status: str


class TaskCreateIn(BaseModel):
    title: str
    assignee: str = ""


class TaskUpdateIn(BaseModel):
    status: str | None = None
    assignee: str | None = None


@router.get("/tasks", response_model=list[TaskOut])
async def get_team_tasks(session: AsyncSession = Depends(get_session)) -> list[TaskOut]:
    from app.services.team_tasks import ensure_seed_tasks, list_tasks

    brand = await ensure_seed(session)
    await ensure_seed_tasks(session, brand)
    return [TaskOut.model_validate(t, from_attributes=True) for t in await list_tasks(session)]


@router.post("/tasks", response_model=TaskOut)
async def post_team_task(
    payload: TaskCreateIn, session: AsyncSession = Depends(get_session)
) -> TaskOut:
    from app.services.team_tasks import create_task

    brand = await ensure_seed(session)
    task = await create_task(session, brand, title=payload.title, assignee=payload.assignee)
    return TaskOut.model_validate(task, from_attributes=True)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_team_task(
    task_id: UUID, payload: TaskUpdateIn, session: AsyncSession = Depends(get_session)
) -> TaskOut:
    from app.services.team_tasks import update_task

    task = await update_task(session, task_id, status=payload.status, assignee=payload.assignee)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskOut.model_validate(task, from_attributes=True)


class InsightOut(BaseModel):
    kind: str
    severity: str
    title: str
    detail: str


@router.get("/insights", response_model=list[InsightOut])
async def get_insights(session: AsyncSession = Depends(get_session)) -> list[InsightOut]:
    """Recompute + return reflection-job insights (Build Spec §8.12)."""
    from app.services.insights import generate_insights

    brand = await ensure_seed(session)
    rows = await generate_insights(session, brand)
    return [InsightOut.model_validate(r, from_attributes=True) for r in rows]


# --- Flows (configurable CS SOPs) ---
class FlowOut(BaseModel):
    id: UUID
    name: str
    intent: str
    enabled: bool
    triggers: list[str] | None
    escalate_keywords: list[str] | None
    steps: list[dict[str, object]] | None


class FlowIn(BaseModel):
    name: str
    enabled: bool
    triggers: list[str]
    escalate_keywords: list[str]
    steps: list[dict[str, object]]


@router.get("/flows", response_model=list[FlowOut])
async def get_flows(session: AsyncSession = Depends(get_session)) -> list[FlowOut]:
    """List the brand's CS flows (seeded with WISMO + refund-deflection)."""
    from app.services.flow_engine import list_flows
    from app.services.flow_seeds import ensure_seed_flows

    brand = await ensure_seed(session)
    await ensure_seed_flows(session, brand)
    return [FlowOut.model_validate(f, from_attributes=True) for f in await list_flows(session)]


@router.put("/flows/{flow_id}", response_model=FlowOut)
async def put_flow(
    flow_id: UUID, payload: FlowIn, session: AsyncSession = Depends(get_session)
) -> FlowOut:
    from app.services.flow_engine import update_flow

    flow = await update_flow(
        session,
        flow_id,
        name=payload.name,
        enabled=payload.enabled,
        triggers=payload.triggers,
        escalate_keywords=payload.escalate_keywords,
        steps=payload.steps,
    )
    if flow is None:
        raise HTTPException(status_code=404, detail="flow not found")
    return FlowOut.model_validate(flow, from_attributes=True)


class ChatIn(BaseModel):
    message: str


@router.post("/chat")
async def post_chat(
    payload: ChatIn, session: AsyncSession = Depends(get_session)
) -> dict[str, object]:
    """Read-only copilot over Shopify + vault (Build Spec §7.4). No writes."""
    from app.services.chat import answer

    await ensure_seed(session)
    return await answer(session, payload.message)


@router.get("/agents/templates")
async def get_agent_templates() -> list[dict[str, object]]:
    from app.services.agents_config import list_templates

    return list_templates()


@router.get("/agents", response_model=list[AgentOut])
async def get_agents(session: AsyncSession = Depends(get_session)) -> list[AgentOut]:
    from app.services.agents_config import ensure_seed_agents, list_agents

    brand = await ensure_seed(session)
    await ensure_seed_agents(session, brand)
    return [AgentOut.model_validate(a, from_attributes=True) for a in await list_agents(session)]


@router.put("/agents/{agent_id}", response_model=AgentOut)
async def put_agent(
    agent_id: UUID, payload: AgentIn, session: AsyncSession = Depends(get_session)
) -> AgentOut:
    from app.services.agents_config import update_agent

    agent = await update_agent(
        session,
        agent_id,
        voice=payload.voice,
        sops=payload.sops,
        schedule=payload.schedule,
        enabled=payload.enabled,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return AgentOut.model_validate(agent, from_attributes=True)
