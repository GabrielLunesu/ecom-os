"""Invariant tests for the connector layer (Build Spec §2).

Covers the security-critical, tests-first guarantees:
  - Invariant 1: only connection *references* are modeled; no raw creds on the ref.
  - Invariant 2: the CS-facing connector has no refund capability; refunds are a
    separate, approval-gated executor.
  - Invariant 5: secrets never serialize/log in plaintext.
"""

from __future__ import annotations

import json

import pytest

from app.services.connectors import (
    ConnectionRef,
    DirectShopifyConnector,
    RefundExecutor,
    RefundNotApprovedError,
    Secret,
    SecretResolutionError,
    ShopifyConnector,
    resolve_secret,
    shopify_connector_for,
)

TOKEN = "shpat_supersecrettoken_should_never_leak"


@pytest.fixture
def shopify_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("SHOPIFY_STORE_URL", "stv0xe-c4.myshopify.com")


# --- Invariant 5: no secret logged or returned in plaintext ----------------
def test_secret_never_renders_value() -> None:
    s = Secret(TOKEN)
    assert TOKEN not in repr(s)
    assert TOKEN not in str(s)
    assert TOKEN not in f"{s}"
    assert TOKEN not in "{}".format(s)
    assert str(s) == "***REDACTED***"
    # Reveal is the single explicit escape hatch.
    assert s.reveal() == TOKEN


def test_secret_not_exposed_via_json_or_dict() -> None:
    s = Secret(TOKEN)
    payload = {"token": str(s), "note": f"value is {s}"}
    dumped = json.dumps(payload)
    assert TOKEN not in dumped


def test_connector_repr_does_not_leak_token(shopify_env: None) -> None:
    conn = DirectShopifyConnector.from_env()
    assert TOKEN not in repr(conn)
    assert TOKEN not in str(vars(conn))
    # The token is held as a Secret, not a bare string.
    assert isinstance(conn._token, Secret)  # noqa: SLF001 - asserting internal safety


def test_resolve_secret_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    with pytest.raises(SecretResolutionError):
        resolve_secret("SHOPIFY_ACCESS_TOKEN")


# --- Invariant 1: connection references only -------------------------------
def test_connection_ref_holds_only_reference() -> None:
    ref = ConnectionRef(provider="direct", external_id="stv0xe-c4.myshopify.com")
    # The ref carries no credential material — only provider + external id.
    assert set(vars(ref)) == {"provider", "external_id"}
    assert TOKEN not in json.dumps(vars(ref))


def test_connection_ref_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown connection provider"):
        ConnectionRef(provider="raw-creds", external_id="x")
    with pytest.raises(ValueError):
        ConnectionRef(provider="direct", external_id="")


def test_registry_builds_direct_connector_from_ref(shopify_env: None) -> None:
    ref = ConnectionRef(provider="direct", external_id="stv0xe-c4.myshopify.com")
    conn = shopify_connector_for(ref)
    assert isinstance(conn, ShopifyConnector)


# --- Invariant 2: CS agent has no refund tool ------------------------------
def test_shopify_connector_has_no_refund_capability(shopify_env: None) -> None:
    conn = DirectShopifyConnector.from_env()
    for forbidden in ("refund", "create_refund", "cancel_order", "delete_order"):
        assert not hasattr(conn, forbidden), f"CS connector must not expose {forbidden}"


def test_shopify_connector_exposes_only_read_and_discount() -> None:
    methods = {
        n
        for n in dir(ShopifyConnector)
        if not n.startswith("_") and callable(getattr(ShopifyConnector, n))
    }
    assert methods == {
        "get_shop",
        "get_order",
        "search_orders",
        "get_fulfillments",
        "create_discount",
    }


def test_refund_executor_is_separate_and_gated() -> None:
    ex = RefundExecutor(
        ConnectionRef(provider="direct", external_id="stv0xe-c4.myshopify.com")
    )
    # Not a ShopifyConnector — never handed to the CS agent.
    assert not isinstance(ex, ShopifyConnector)


@pytest.mark.asyncio
async def test_refund_requires_approval() -> None:
    ex = RefundExecutor(ConnectionRef(provider="direct", external_id="x.myshopify.com"))
    with pytest.raises(RefundNotApprovedError):
        await ex.execute(None)
