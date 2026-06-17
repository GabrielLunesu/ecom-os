"""Refund approval lane (Invariant 2).

A refund is requested (pending), a human approves or rejects it, and only on
approval does the separately-scoped RefundExecutor run. The CS agent has no path
into this module — it cannot create or approve refunds.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.core.time import utcnow
from app.models.brand import Brand
from app.models.refunds import RefundRequest
from app.services.connectors.refunds import RefundApproval, RefundExecutor

logger = get_logger(__name__)


async def create_refund_request(
    session: AsyncSession,
    *,
    brand: Brand,
    order_id: str,
    order_name: str,
    amount: float,
    currency: str,
    reason: str,
    requested_by: str,
    ticket_id: UUID | None = None,
) -> RefundRequest:
    req = RefundRequest(
        brand_id=brand.id,
        ticket_id=ticket_id,
        order_id=order_id,
        order_name=order_name,
        amount=amount,
        currency=currency,
        reason=reason,
        requested_by=requested_by,
        status="pending",
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def list_refunds(session: AsyncSession) -> list[RefundRequest]:
    return list(
        (await session.exec(select(RefundRequest).order_by(RefundRequest.created_at.desc()))).all()  # type: ignore[attr-defined]
    )


async def reject_refund(session: AsyncSession, refund_id: UUID, approver: str) -> RefundRequest:
    req = (await session.exec(select(RefundRequest).where(RefundRequest.id == refund_id))).first()
    if req is None:
        raise ValueError("refund request not found")
    req.status = "rejected"
    req.approved_by = approver
    req.resolved_at = utcnow()
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def approve_refund(
    session: AsyncSession,
    refund_id: UUID,
    approver: str,
    executor: RefundExecutor,
) -> RefundRequest:
    """Approve and execute. Execution uses the separately-scoped RefundExecutor;
    a failure (e.g. no refund connection provisioned) is recorded, not silent."""
    req = (await session.exec(select(RefundRequest).where(RefundRequest.id == refund_id))).first()
    if req is None:
        raise ValueError("refund request not found")
    if req.status not in ("pending", "approved"):
        raise ValueError(f"cannot approve a {req.status} refund")

    req.status = "approved"
    req.approved_by = approver
    session.add(req)
    await session.commit()

    approval = RefundApproval(
        approval_id=str(req.id),
        order_id=req.order_id,
        amount=req.amount,
        approved_by=approver,
    )
    try:
        await executor.execute(approval)
        req.status = "executed"
        req.resolved_at = utcnow()
    except Exception as exc:  # noqa: BLE001 - record the failure on the request
        logger.warning("refund execution failed for %s: %s", req.id, type(exc).__name__)
        req.status = "failed"
        req.error = f"{type(exc).__name__}: {exc}"
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req
