"""Tests for the §1.5 bootstrap gate: refuse the CS loop until both live."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand, Store
from app.services import connection_health as ch
from app.services.connection_health import (
    CSLoopNotReady,
    ProviderHealth,
    assert_ready_for_cs_loop,
    connections_status,
)
from app.services.connectors.base import ShopifyConnector
from app.services.connectors.secrets import ConnectionRef


@pytest.fixture
def both_up(monkeypatch: pytest.MonkeyPatch) -> None:
    async def shop() -> ProviderHealth:
        return ProviderHealth("shopify", True, "connected: CHICAGO OUTLET")

    async def inbox() -> ProviderHealth:
        return ProviderHealth("inbox", True, "outlook: ACTIVE")

    monkeypatch.setattr(ch, "check_shopify", shop)
    monkeypatch.setattr(ch, "check_inbox", inbox)


@pytest.fixture
def inbox_down(monkeypatch: pytest.MonkeyPatch) -> None:
    async def shop() -> ProviderHealth:
        return ProviderHealth("shopify", True, "connected: CHICAGO OUTLET")

    async def inbox() -> ProviderHealth:
        return ProviderHealth("inbox", False, "no active mail account")

    monkeypatch.setattr(ch, "check_shopify", shop)
    monkeypatch.setattr(ch, "check_inbox", inbox)


@pytest.mark.asyncio
async def test_status_ready_when_both_up(both_up: None) -> None:
    status = await connections_status()
    assert status["ready"] is True
    await assert_ready_for_cs_loop()  # does not raise


@pytest.mark.asyncio
async def test_gate_blocks_when_inbox_down(inbox_down: None) -> None:
    status = await connections_status()
    assert status["ready"] is False
    with pytest.raises(CSLoopNotReady, match="inbox"):
        await assert_ready_for_cs_loop()


@pytest.mark.asyncio
async def test_status_payload_carries_no_secret(both_up: None) -> None:
    import json

    dumped = json.dumps(await connections_status())
    for marker in ("shpat_", "Bearer", "x-api-key", "access_token"):
        assert marker not in dumped


async def _session() -> AsyncSession:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False)


class FakeShopify(ShopifyConnector):
    async def get_shop(self) -> dict[str, object]:
        return {"name": "CHICAGO OUTLET"}

    async def get_order(self, order_id: str) -> dict[str, object]:
        return {}

    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, object]]:
        return []

    async def get_fulfillments(self, order_id: str) -> list[dict[str, object]]:
        return []

    async def list_orders(
        self,
        *,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
        limit: int = 250,
    ) -> list[dict[str, object]]:
        return []

    async def create_discount(
        self, *, title: str, percentage: float, code: str
    ) -> dict[str, object]:
        return {}


@pytest.mark.asyncio
async def test_shopify_health_uses_db_store_ref_before_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with await _session() as session:
        brand = Brand(name="Test")
        session.add(brand)
        await session.flush()
        session.add(
            Store(
                brand_id=brand.id,
                name="Chicago Outlet Shop",
                domain="stv0xe-c4.myshopify.com",
                provider="direct",
                external_id="stv0xe-c4.myshopify.com",
                status="connected",
            )
        )
        await session.commit()

        def fake_connector(ref: ConnectionRef) -> ShopifyConnector:
            assert ref.external_id == "stv0xe-c4.myshopify.com"
            return FakeShopify(ref)

        monkeypatch.setattr(ch, "shopify_connector_for", fake_connector)

        health = await ch.check_shopify(session)
        assert health.connected is True
        assert health.detail == "connected: CHICAGO OUTLET"
