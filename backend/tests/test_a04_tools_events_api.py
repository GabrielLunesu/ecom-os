# ruff: noqa
"""A04 — read tools, inbox/message event emission, and the commerce API."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.connectors.adapters.fake import FakeProviderBackend, build_fake_registry
from app.connectors.api import router as commerce_router
from app.connectors.binding import ConnectionBinding
from app.connectors.durable import LocalDurableInbox
from app.connectors.events import CollectingSink, ingest_inbox_messages
from app.connectors.models import Connection
from app.connectors.read_repository import CommerceReadRepository
from app.connectors.sync import SyncEngine
from app.connectors.tools import CommerceReadTools, READ_TOOL_MANIFEST
from app.db.session import get_session
from tests.a04_helpers import open_session


def _order(ext="1001", email="amy@x.com"):
    return {
        "external_id": ext, "order_number": f"#{ext}", "email": email, "currency": "USD",
        "total_minor": 4999, "subtotal_minor": 4999, "financial_status": "paid",
        "fulfillment_status": "fulfilled", "placed_at": datetime(2024, 1, 1),
        "source_updated_at": datetime(2024, 1, 2), "customer": {
            "external_id": "cust-9", "email": email, "name": "Amy", "orders_count": 1,
            "source_updated_at": None}, "lines": [], "fulfillments": [],
    }


async def _seed(session, store_id, connection_id, healthy=True):
    session.add(Connection(
        id=connection_id, brand_id=uuid4(), store_id=store_id, provider="fake",
        capability="store", account_ref="store-A", adapter_version="v1",
        status="connected" if healthy else "disconnected", last_health_ok=healthy))
    await session.flush()


def _binding(store_id, connection_id, account="store-A", capability="store"):
    return ConnectionBinding(
        brand_id=uuid4(), store_id=store_id, connection_id=connection_id, provider="fake",
        capability=capability, account_ref=account, adapter_version="v1")


def test_read_tool_manifest_is_read_only() -> None:
    names = {t.name for t in READ_TOOL_MANIFEST}
    assert {"ecom.store.list", "ecom.order.get", "ecom.order.search", "ecom.customer.get"} <= names
    assert all(t.read_or_write == "read" for t in READ_TOOL_MANIFEST)


@pytest.mark.asyncio
async def test_read_tools_return_evidence_envelopes() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        await _seed(session, store_id, connection_id)
        reg = build_fake_registry({"store-A": FakeProviderBackend("store-A", orders=[_order()])})
        binding = _binding(store_id, connection_id)
        await SyncEngine(session).sync_orders(binding, reg.resolve(binding))
        await session.commit()

        tools = CommerceReadTools(CommerceReadRepository(session))
        got = await tools.order_get(store_id, "1001")
        assert got["ok"] and got["status"] == "completed"
        assert got["data"]["order_number"] == "#1001"
        assert got["evidence"][0]["reference"] == "fake:order:1001"
        assert got["freshness"]["status"] == "current"

        missing = await tools.order_get(store_id, "nope")
        assert missing["data"] is None and "not_found" in missing["warnings"]


@pytest.mark.asyncio
async def test_inbox_events_emitted_once_and_untrusted() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        msgs = [
            {"external_id": "m1", "conversation_id": "c1", "from_email": "x@y.com",
             "from_name": "X", "subject": "Where is my order?", "body_text": "hi",
             "received_at": "2024-01-01T00:00:00Z", "is_read": False},
        ]
        backend = FakeProviderBackend("ca_1")
        backend.resources["messages"] = msgs
        reg = build_fake_registry({"ca_1": backend}, capability="inbox", provider="fake")
        binding = _binding(store_id, connection_id, account="ca_1", capability="inbox")
        port = reg.resolve(binding)
        inbox = LocalDurableInbox(session)
        sink = CollectingSink()

        first = await ingest_inbox_messages(port, inbox, binding, sink)
        second = await ingest_inbox_messages(port, inbox, binding, sink)  # duplicate poll
        await session.commit()

        assert len(first) == 1 and len(second) == 0  # emitted once
        assert len(sink.events) == 1
        assert sink.events[0].untrusted is True
        assert sink.events[0].subject == "Where is my order?"


@pytest.mark.asyncio
async def test_commerce_api_orders_and_not_found() -> None:
    async with open_session() as session:
        store_id, connection_id = uuid4(), uuid4()
        await _seed(session, store_id, connection_id)
        reg = build_fake_registry({"store-A": FakeProviderBackend("store-A", orders=[_order()])})
        binding = _binding(store_id, connection_id)
        await SyncEngine(session).sync_orders(binding, reg.resolve(binding))
        await session.commit()

        app = FastAPI()
        app.include_router(commerce_router)
        app.dependency_overrides[get_session] = lambda: session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            ok = await client.get(f"/api/v1/ecom/commerce/stores/{store_id}/orders/1001")
            assert ok.status_code == 200
            body = ok.json()
            assert body["data"]["order_number"] == "#1001"
            assert body["evidence"][0]["source"] == "fake"

            missing = await client.get(f"/api/v1/ecom/commerce/stores/{store_id}/orders/zzz")
            assert missing.status_code == 404

            stores = await client.get("/api/v1/ecom/commerce/stores")
            assert stores.status_code == 200
            assert stores.json()["data"][0]["connections"][0]["provider"] == "fake"
