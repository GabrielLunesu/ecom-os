"""A01 foundation: health primitives and readiness endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, Response, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.health import (
    HealthState,
    build_readiness_report,
    check_database,
    check_migrations,
)
from app.db.session import get_session
from app.schemas.health import ComponentHealthModel, HealthReportResponse, HealthStatusResponse


@pytest_asyncio.fixture
async def maker(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'health.db'}")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
class TestHealthPrimitives:
    async def test_database_ok(self, maker: async_sessionmaker[AsyncSession]) -> None:
        async with maker() as session:
            result = await check_database(session)
        assert result.state is HealthState.OK

    async def test_migrations_unknown_without_alembic_table(
        self,
        maker: async_sessionmaker[AsyncSession],
    ) -> None:
        # create_all does not stamp alembic_version, so state is unknown (honest).
        async with maker() as session:
            result = await check_migrations(session)
        assert result.state is HealthState.UNKNOWN

    async def test_readiness_report_overall_ok_and_lists_dimensions(
        self,
        maker: async_sessionmaker[AsyncSession],
    ) -> None:
        async with maker() as session:
            overall, components = await build_readiness_report(session)
        assert overall is HealthState.OK
        names = {c.name for c in components}
        # Owned dimensions plus honest placeholders for other domains.
        assert {"liveness", "database", "migrations"} <= names
        assert {"connectors", "queue_and_leases", "hermes_compatibility"} <= names
        assert any(c.state is HealthState.UNKNOWN for c in components)


def _health_app(maker: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()

    async def _get_session() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    @app.get("/readyz", response_model=HealthStatusResponse)
    async def readyz(
        response: Response,
        session: AsyncSession = Depends(_get_session),
    ) -> HealthStatusResponse:
        overall, _ = await build_readiness_report(session)
        ready = overall is not HealthState.DOWN
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatusResponse(ok=ready)

    @app.get("/readyz/details", response_model=HealthReportResponse)
    async def readyz_details(
        response: Response,
        session: AsyncSession = Depends(_get_session),
    ) -> HealthReportResponse:
        overall, components = await build_readiness_report(session)
        ready = overall is not HealthState.DOWN
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthReportResponse(
            state=overall.value,
            ready=ready,
            components=[ComponentHealthModel(**c.as_dict()) for c in components],
        )

    app.dependency_overrides[get_session] = _get_session
    return app


@pytest.mark.asyncio
async def test_readyz_endpoints(maker: async_sessionmaker[AsyncSession]) -> None:
    app = _health_app(maker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ready = await client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json()["ok"] is True

        details = await client.get("/readyz/details")
        assert details.status_code == 200
        body = details.json()
        assert body["ready"] is True
        assert body["state"] == "ok"
        names = {c["name"] for c in body["components"]}
        assert "database" in names and "backup_freshness" in names
