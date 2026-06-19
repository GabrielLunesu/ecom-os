# ruff: noqa
"""A04 — sync idempotency + evidence-backed reads + last-good-on-outage."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlmodel import func, select

from app.connectors.adapters.fake import FakeProviderBackend, build_fake_registry
from app.connectors.binding import ConnectionBinding
from app.connectors.models import Connection, Order
from app.connectors.read_repository import CommerceReadRepository
from app.connectors.sync import SyncEngine
from tests.a04_helpers import open_session


def _order_record(ext: str = "1001", email: str = "amy@x.com") -> dict:
    return {
        "external_id": ext,
        "order_number": f"#{ext}",
        "email": email,
        "currency": "USD",
        "total_minor": 4999,
        "subtotal_minor": 4999,
        "financial_status": "paid",
        "fulfillment_status": "fulfilled",
        "placed_at": datetime(2024, 1, 1, 12, 0, 0),
        "source_updated_at": datetime(2024, 1, 2, 12, 0, 0),
        "customer": {
            "external_id": "cust-9",
            "email": email,
            "name": "Amy Shopper",
            "orders_count": 2,
            "source_updated_at": datetime(2024, 1, 1, 0, 0, 0),
        },
        "lines": [
            {
                "external_id": "li-1",
                "title": "Sneaker",
                "sku": "SNK",
                "quantity": 1,
                "price_minor": 4999,
                "product_external_id": "p-1",
            }
        ],
        "fulfillments": [
            {
                "external_id": "f-1",
                "status": "success",
                "tracking_company": "USPS",
                "tracking_number": "TRK1",
                "tracking_url": "http://t/1",
                "shipped_at": datetime(2024, 1, 2, 0, 0, 0),
                "source_updated_at": None,
            }
        ],
    }


async def _seed_connection(session, *, store_id, connection_id, account="store-A", healthy=True):
    conn = Connection(
        id=connection_id,
        brand_id=uuid4(),
        store_id=store_id,
        provider="fake",
        capability="store",
        account_ref=account,
        adapter_version="v1",
        status="connected" if healthy else "disconnected",
        last_health_ok=healthy,
    )
    session.add(conn)
    await session.flush()
    return conn


def _binding(store_id, connection_id, account="store-A"):
    return ConnectionBinding(
        brand_id=uuid4(),
        store_id=store_id,
        connection_id=connection_id,
        provider="fake",
        capability="store",
        account_ref=account,
        adapter_version="v1",
    )


@pytest.mark.asyncio
async def test_order_retrieved_by_id_and_customer_with_evidence() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        await _seed_connection(session, store_id=store_id, connection_id=connection_id)
        backend = FakeProviderBackend("store-A", orders=[_order_record()])
        reg = build_fake_registry({"store-A": backend})
        binding = _binding(store_id, connection_id)
        port = reg.resolve(binding)

        report = await SyncEngine(session).sync_orders(binding, port)
        await session.commit()
        assert report.processed == 1 and report.created == 1

        repo = CommerceReadRepository(session)

        # by provider external id
        by_id = await repo.get_order(store_id, "1001")
        assert by_id is not None
        env = by_id.to_envelope()
        assert env["data"]["order_number"] == "#1001"
        assert env["data"]["total_minor"] == 4999
        assert env["data"]["lines"][0]["sku"] == "SNK"
        assert env["data"]["fulfillments"][0]["tracking_number"] == "TRK1"
        # source + freshness + evidence are present and honest
        assert env["coverage"] == "imported"
        assert env["freshness"]["status"] == "current"
        assert env["evidence"][0]["source"] == "fake"
        assert env["evidence"][0]["reference"] == "fake:order:1001"
        assert env["evidence"][0]["content_hash"].startswith("sha256:")

        # by order number
        assert (await repo.get_order(store_id, "#1001")) is not None

        # by customer email
        by_cust = await repo.find_orders_by_customer(store_id, "amy@x.com")
        cenv = by_cust.to_envelope()
        assert len(cenv["data"]) == 1
        assert cenv["data"][0]["order_number"] == "#1001"
        assert cenv["evidence"][0]["source_id"] == "1001"

        cust = await repo.get_customer(store_id, "amy@x.com")
        assert cust is not None and cust.data["name"] == "Amy Shopper"


@pytest.mark.asyncio
async def test_duplicate_event_changes_state_once() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        await _seed_connection(session, store_id=store_id, connection_id=connection_id)
        backend = FakeProviderBackend("store-A", orders=[_order_record()])
        reg = build_fake_registry({"store-A": backend})
        binding = _binding(store_id, connection_id)
        port = reg.resolve(binding)
        engine = SyncEngine(session)

        # Apply the same provider event twice (e.g. duplicate webhook).
        await engine.apply_order_event(binding, port, "1001")
        await engine.apply_order_event(binding, port, "1001")
        await session.commit()

        count = int((await session.exec(select(func.count()).select_from(Order))).one())
        assert count == 1  # one normalized row, not two (I-07)


@pytest.mark.asyncio
async def test_outage_returns_last_good_marked_stale() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        # Sync while healthy...
        await _seed_connection(
            session, store_id=store_id, connection_id=connection_id, healthy=True
        )
        backend = FakeProviderBackend("store-A", orders=[_order_record()])
        reg = build_fake_registry({"store-A": backend})
        binding = _binding(store_id, connection_id)
        await SyncEngine(session).sync_orders(binding, reg.resolve(binding))
        await session.commit()

        # ...then the connection goes down (outage).
        conn = await session.get(Connection, connection_id)
        conn.status = "disconnected"
        conn.last_health_ok = False
        session.add(conn)
        await session.commit()

        repo = CommerceReadRepository(session)
        result = await repo.get_order(store_id, "1001")
        assert result is not None
        env = result.to_envelope()
        # Last-good data is still returned, but explicitly marked stale, not current.
        assert env["data"]["order_number"] == "#1001"
        assert env["freshness"]["status"] == "stale"
        assert env["freshness"]["as_of"] is not None


@pytest.mark.asyncio
async def test_incremental_sync_updates_not_duplicates() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        await _seed_connection(session, store_id=store_id, connection_id=connection_id)
        backend = FakeProviderBackend("store-A", orders=[_order_record()])
        reg = build_fake_registry({"store-A": backend})
        binding = _binding(store_id, connection_id)
        engine = SyncEngine(session)

        await engine.sync_orders(binding, reg.resolve(binding))
        # Order updates upstream (status change), re-sync.
        backend.resources["orders"][0]["fulfillment_status"] = "delivered"
        await engine.sync_orders(binding, reg.resolve(binding))
        await session.commit()

        count = int((await session.exec(select(func.count()).select_from(Order))).one())
        assert count == 1
        order = (await session.exec(select(Order))).first()
        assert order.fulfillment_status == "delivered"
