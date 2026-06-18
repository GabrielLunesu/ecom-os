# ruff: noqa
"""A04 — exact account binding, provider-independent registry, normalization."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.connectors.adapters.fake import FakeProviderBackend, build_fake_registry
from app.connectors.adapters.shopify import normalize_order
from app.connectors.binding import ConnectionBinding
from app.connectors.errors import CapabilityUnsupported, ConnectorBindingError
from app.connectors.models import Connection
from app.connectors.registry import default_registry
from tests.a04_helpers import mk_binding


@pytest.mark.parametrize("bad", ["", "default", "latest", "any", "*", "most_recent", "  "])
def test_binding_rejects_non_exact_account(bad: str) -> None:
    with pytest.raises(ConnectorBindingError):
        mk_binding(bad)


def test_binding_requires_scope_fields() -> None:
    with pytest.raises(ConnectorBindingError):
        ConnectionBinding(
            brand_id=uuid4(),
            store_id=uuid4(),
            connection_id=uuid4(),
            provider="",  # missing provider
            capability="store",
            account_ref="store-A",
            adapter_version="v1",
        )


def test_require_account_rejects_wrong_account() -> None:
    binding = mk_binding("store-A")
    binding.require_account("store-A")  # ok
    with pytest.raises(ConnectorBindingError):
        binding.require_account("store-B")


def test_from_connection_fails_closed_when_disconnected() -> None:
    conn = Connection(
        brand_id=uuid4(),
        store_id=uuid4(),
        provider="direct",
        capability="store",
        account_ref="shop.myshopify.com",
        adapter_version="shopify-direct-2025-01",
        status="disconnected",
    )
    with pytest.raises(ConnectorBindingError):
        ConnectionBinding.from_connection(conn)
    conn.status = "connected"
    binding = ConnectionBinding.from_connection(conn)
    assert binding.account_ref == "shop.myshopify.com"


def test_default_registry_resolves_direct_store_but_not_managed_store() -> None:
    reg = default_registry()
    assert reg.supports("direct", "store")
    assert reg.supports("composio", "inbox")
    # Managed Shopify OAuth is not wired yet => fail closed, not a silent default.
    assert not reg.supports("composio", "store")
    with pytest.raises(CapabilityUnsupported):
        reg.resolve(mk_binding("acct", provider="composio", capability="store"))


@pytest.mark.asyncio
async def test_registry_wrong_account_fails_closed() -> None:
    backend = FakeProviderBackend("store-A")
    reg = build_fake_registry({"store-A": backend})
    # An unknown bound account resolves to no connected account => rejected.
    with pytest.raises(ConnectorBindingError):
        reg.resolve(mk_binding("store-B"))


@pytest.mark.asyncio
async def test_fake_adapter_rejects_wrong_account_on_read() -> None:
    # Backend's true account differs from the binding's account => fail closed.
    from app.connectors.adapters.fake import FakeCommerceAdapter

    backend = FakeProviderBackend("real-account")
    adapter = FakeCommerceAdapter(mk_binding("spoofed-account"), backend)
    with pytest.raises(ConnectorBindingError):
        await adapter.fetch_one("orders", "1")


def test_shopify_normalization_minor_units_and_tz() -> None:
    raw = {
        "id": 450789469,
        "name": "#1001",
        "email": "b@x.com",
        "currency": "USD",
        "total_price": "199.99",
        "subtotal_price": "180.00",
        "financial_status": "paid",
        "fulfillment_status": "partial",
        "created_at": "2024-01-02T11:00:00-05:00",
        "updated_at": "2024-01-03T09:00:00-05:00",
        "line_items": [
            {"id": 1, "title": "Boot", "sku": "BT1", "quantity": 2, "price": "90.00", "product_id": 7}
        ],
        "customer": {
            "id": 99,
            "email": "b@x.com",
            "first_name": "Bo",
            "last_name": "Le",
            "orders_count": 3,
            "updated_at": "2024-01-01T00:00:00Z",
        },
        "fulfillments": [
            {
                "id": 5,
                "status": "success",
                "tracking_company": "UPS",
                "tracking_numbers": ["1Z999"],
                "tracking_urls": ["http://t"],
                "created_at": "2024-01-03T00:00:00Z",
            }
        ],
    }
    n = normalize_order(raw)
    assert n["external_id"] == "450789469"
    assert n["total_minor"] == 19999  # integer minor units, no float drift
    assert n["subtotal_minor"] == 18000
    assert n["placed_at"].hour == 16  # -05:00 normalized to UTC
    assert n["customer"]["name"] == "Bo Le"
    assert n["fulfillments"][0]["tracking_number"] == "1Z999"
    # Raw provider keys never survive normalization.
    assert "total_price" not in n and "line_items" not in n


def test_shopify_normalization_rejects_missing_id() -> None:
    from app.connectors.errors import ProviderPayloadError

    with pytest.raises(ProviderPayloadError):
        normalize_order({"name": "#x"})
