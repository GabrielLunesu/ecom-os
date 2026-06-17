"""Secret store tests: encrypted at rest, never exposed, cache fallback, per-store.

Hermetic — in-memory sqlite, no network (mirrors tests/test_cs_runtime.py).
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand
from app.models.secret_entry import SecretEntry
from app.services import secret_store
from app.services.connectors.secrets import resolve_secret
from app.services.secret_store import (
    get_cached,
    list_handles,
    load_secret_cache,
    set_secret,
    unset_secret,
)

PLAINTEXT = "shpat_super_secret_value_should_never_leak"


async def _seeded_session() -> tuple[AsyncSession, Brand]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    brand = Brand(name="Test")
    session.add(brand)
    await session.flush()
    await session.commit()
    return session, brand


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    secret_store._CACHE.clear()
    yield
    # Don't leak module-global cache state into other test files.
    secret_store._CACHE.clear()


@pytest.mark.asyncio
async def test_set_secret_encrypts_at_rest_and_caches() -> None:
    session, brand = await _seeded_session()
    await set_secret(session, brand, "COMPOSIO_API_KEY", PLAINTEXT)

    assert get_cached("COMPOSIO_API_KEY") == PLAINTEXT

    row = (
        await session.exec(
            select(SecretEntry).where(SecretEntry.handle == "COMPOSIO_API_KEY")
        )
    ).first()
    assert row is not None
    # Stored ciphertext is encrypted, not the plaintext.
    assert PLAINTEXT not in row.ciphertext
    assert row.ciphertext != PLAINTEXT


@pytest.mark.asyncio
async def test_list_handles_never_exposes_value() -> None:
    session, brand = await _seeded_session()
    await set_secret(session, brand, "COMPOSIO_API_KEY", PLAINTEXT)

    handles = await list_handles(session)
    assert handles == ["COMPOSIO_API_KEY"]
    # The plaintext appears nowhere in what we return.
    assert PLAINTEXT not in json.dumps(handles)


@pytest.mark.asyncio
async def test_unset_secret_clears_cache_and_row() -> None:
    session, brand = await _seeded_session()
    await set_secret(session, brand, "COMPOSIO_API_KEY", PLAINTEXT)
    await unset_secret(session, brand, "COMPOSIO_API_KEY")

    assert get_cached("COMPOSIO_API_KEY") is None
    assert await list_handles(session) == []


@pytest.mark.asyncio
async def test_load_secret_cache_decrypts_all() -> None:
    session, brand = await _seeded_session()
    await set_secret(session, brand, "COMPOSIO_API_KEY", PLAINTEXT)
    secret_store._CACHE.clear()
    assert get_cached("COMPOSIO_API_KEY") is None

    await load_secret_cache(session)
    assert get_cached("COMPOSIO_API_KEY") == PLAINTEXT


def test_resolve_secret_falls_back_to_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    monkeypatch.setattr(settings, "composio_api_key", "", raising=False)
    secret_store._CACHE["COMPOSIO_API_KEY"] = PLAINTEXT

    secret = resolve_secret("COMPOSIO_API_KEY")
    assert secret.reveal() == PLAINTEXT


def _no_client_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the static-token path: no client-credentials anywhere + clear caches."""
    from app.core.config import settings
    from app.services.connectors import shopify_token

    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(settings, "shopify_access_token", "", raising=False)
    for var in ("SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET", "SHOPIFY_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(settings, var.lower(), "", raising=False)
    shopify_token._TOKEN_CACHE.clear()


@pytest.mark.asyncio
async def test_per_store_token_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.connectors.shopify_token import get_store_token

    _no_client_creds(monkeypatch)
    domain = "store-x.myshopify.com"
    secret_store._CACHE[f"SHOPIFY_ACCESS_TOKEN:{domain}"] = "per-store-token"
    tok = await get_store_token(domain)
    assert tok.reveal() == "per-store-token"  # per-store handle wins


@pytest.mark.asyncio
async def test_per_store_falls_back_to_global(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.connectors.shopify_token import get_store_token

    _no_client_creds(monkeypatch)
    domain = "store-y.myshopify.com"
    secret_store._CACHE["SHOPIFY_ACCESS_TOKEN"] = "global-token"
    tok = await get_store_token(domain)
    assert tok.reveal() == "global-token"  # falls back to the global static token
