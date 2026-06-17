"""Shopify token acquisition: client-credentials (no browser) + static fallback."""

from __future__ import annotations

import pytest

from app.services.connectors import shopify_token
from app.services.connectors.secrets import Secret
from app.services.connectors.shopify_token import get_store_token

DOMAIN = "demo.myshopify.com"


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    shopify_token._TOKEN_CACHE.clear()
    yield
    shopify_token._TOKEN_CACHE.clear()


def _no_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    for var in ("SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET", "SHOPIFY_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(settings, var.lower(), "", raising=False)


@pytest.mark.asyncio
async def test_client_credentials_used_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_creds(monkeypatch)
    monkeypatch.setenv("SHOPIFY_CLIENT_ID", "cid")
    monkeypatch.setenv("SHOPIFY_CLIENT_SECRET", "csecret")
    calls = {"n": 0}

    async def fake_fetch(domain: str, client_id: str, client_secret: str) -> tuple[str, int]:
        calls["n"] += 1
        assert (client_id, client_secret) == ("cid", "csecret")
        return "shpat_minted", 86399

    monkeypatch.setattr(shopify_token, "fetch_client_credentials_token", fake_fetch)

    tok = await get_store_token(DOMAIN)
    assert isinstance(tok, Secret) and tok.reveal() == "shpat_minted"
    # Second call hits the cache — no second mint.
    tok2 = await get_store_token(DOMAIN)
    assert tok2.reveal() == "shpat_minted"
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_static_token_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_creds(monkeypatch)
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_static")

    async def boom(*_a: object, **_k: object) -> tuple[str, int]:
        raise AssertionError("client-credentials must not be called without creds")

    monkeypatch.setattr(shopify_token, "fetch_client_credentials_token", boom)
    tok = await get_store_token(DOMAIN)
    assert tok.reveal() == "shpat_static"
