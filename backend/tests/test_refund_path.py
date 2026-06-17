"""Refund-path tests (Invariant 2): separate, approval-gated, own scoped connection."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand
from app.services.connectors.refunds import (
    RefundApproval,
    RefundExecutor,
    RefundNotApprovedError,
)
from app.services.connectors.secrets import ConnectionRef, SecretResolutionError
from app.services.refunds import approve_refund, create_refund_request, reject_refund

REF = ConnectionRef(provider="direct", external_id="x.myshopify.com")


class OkExecutor(RefundExecutor):
    def __init__(self) -> None:
        super().__init__(REF)
        self.calls: list[RefundApproval] = []

    async def execute(self, approval):  # type: ignore[override]
        assert approval is not None  # approval gate upheld by caller
        self.calls.append(approval)
        return {"refund": {"id": 1}}


class FailingExecutor(RefundExecutor):
    def __init__(self) -> None:
        super().__init__(REF)

    async def execute(self, approval):  # type: ignore[override]
        raise SecretResolutionError("no refund connection provisioned")


async def _session() -> tuple[AsyncSession, Brand]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="Test")
    session.add(brand)
    await session.flush()
    return session, brand


async def _request(session: AsyncSession, brand: Brand):
    return await create_refund_request(
        session,
        brand=brand,
        order_id="123",
        order_name="#1001",
        amount=10.0,
        currency="USD",
        reason="late delivery",
        requested_by="operator",
    )


@pytest.mark.asyncio
async def test_executor_requires_approval() -> None:
    ex = RefundExecutor(REF)
    with pytest.raises(RefundNotApprovedError):
        await ex.execute(None)


@pytest.mark.asyncio
async def test_real_executor_needs_its_own_scoped_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # No SHOPIFY_REFUND_ACCESS_TOKEN anywhere -> refund cannot run (own connection).
    from app.core.config import settings

    monkeypatch.delenv("SHOPIFY_REFUND_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(settings, "shopify_refund_access_token", "", raising=False)
    ex = RefundExecutor(REF)
    approval = RefundApproval(approval_id="a", order_id="123", amount=10.0, approved_by="op")
    with pytest.raises(SecretResolutionError):
        await ex.execute(approval)


@pytest.mark.asyncio
async def test_request_is_pending_then_executed_on_approve() -> None:
    session, brand = await _session()
    req = await _request(session, brand)
    assert req.status == "pending"
    ex = OkExecutor()
    approved = await approve_refund(session, req.id, "manager", ex)
    assert approved.status == "executed"
    assert approved.approved_by == "manager"
    assert len(ex.calls) == 1
    assert ex.calls[0].order_id == "123"


@pytest.mark.asyncio
async def test_approve_records_failure_when_execution_errors() -> None:
    session, brand = await _session()
    req = await _request(session, brand)
    approved = await approve_refund(session, req.id, "manager", FailingExecutor())
    assert approved.status == "failed"
    assert "SecretResolutionError" in approved.error


@pytest.mark.asyncio
async def test_reject_does_not_execute() -> None:
    session, brand = await _session()
    req = await _request(session, brand)
    rejected = await reject_refund(session, req.id, "manager")
    assert rejected.status == "rejected"
