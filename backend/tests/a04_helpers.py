# ruff: noqa
"""Shared helpers for A04 connector tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.connectors  # noqa: F401  registers commerce table metadata
from app.connectors.binding import ConnectionBinding


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    """A single-connection in-memory SQLite session (StaticPool => shared DB).

    Disposes the engine on exit so pooled connections are returned cleanly.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def mk_binding(
    account_ref: str = "store-A",
    *,
    provider: str = "fake",
    capability: str = "store",
    brand_id=None,
    store_id=None,
    connection_id=None,
) -> ConnectionBinding:
    return ConnectionBinding(
        brand_id=brand_id or uuid4(),
        store_id=store_id or uuid4(),
        connection_id=connection_id or uuid4(),
        provider=provider,
        capability=capability,
        account_ref=account_ref,
        adapter_version="v1",
    )
