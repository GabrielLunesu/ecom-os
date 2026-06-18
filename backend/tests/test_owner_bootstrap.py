"""A01 foundation: owner bootstrap closes; server-side denial; roles; audit."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.identity import router as identity_router
from app.auth.audit import InMemoryAuditSink, set_audit_sink
from app.auth.roles import ensure_system_roles, user_role_names
from app.core.auth import AuthContext, get_auth_context
from app.core.error_handling import install_error_handling
from app.db.session import get_session
from app.models.identity import BOOTSTRAP_CLOSED, ROLE_OWNER, SYSTEM_ROLES
from app.models.users import User

LOCAL_TOKEN = "test-local-token-0123456789-0123456789-0123456789x"
_AUTH = {"Authorization": f"Bearer {LOCAL_TOKEN}"}


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[object]:
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    async with eng.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


def _build_app(engine: object, *, auth_override: object | None = None) -> FastAPI:
    app = FastAPI()
    install_error_handling(app)
    api = APIRouter(prefix="/api/v1")
    api.include_router(identity_router)
    app.include_router(api)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]

    async def _get_session() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    if auth_override is not None:
        app.dependency_overrides[get_auth_context] = auth_override
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
class TestOwnerBootstrapLocalAuth:
    """End-to-end with the real local-auth mode (genuine server-side enforcement)."""

    async def test_anonymous_cannot_reach_any_identity_route(self, engine: object) -> None:
        app = _build_app(engine)
        async with _client(app) as client:
            for method, path in [
                ("get", "/api/v1/identity/me"),
                ("get", "/api/v1/identity/bootstrap-status"),
                ("post", "/api/v1/identity/owner-bootstrap"),
            ]:
                resp = await client.request(method, path)  # no Authorization header
                assert resp.status_code == 401, (method, path)

    async def test_claim_closes_bootstrap_and_grants_owner(self, engine: object) -> None:
        sink = InMemoryAuditSink()
        set_audit_sink(sink)
        try:
            app = _build_app(engine)
            async with _client(app) as client:
                status = (await client.get("/api/v1/identity/bootstrap-status", headers=_AUTH)).json()
                assert status["is_open"] is True
                assert status["is_owner"] is False

                claim = await client.post("/api/v1/identity/owner-bootstrap", headers=_AUTH)
                assert claim.status_code == 200
                assert claim.json()["role"] == ROLE_OWNER
                assert claim.json()["status"] == BOOTSTRAP_CLOSED

                me = (await client.get("/api/v1/identity/me", headers=_AUTH)).json()
                assert ROLE_OWNER in me["roles"]
                assert "identity:write" in me["scopes"]

                status2 = (await client.get("/api/v1/identity/bootstrap-status", headers=_AUTH)).json()
                assert status2["is_open"] is False
                assert status2["is_owner"] is True
        finally:
            set_audit_sink(InMemoryAuditSink())  # reset global
        assert any(e.action == "owner.bootstrap" for e in sink.events)

    async def test_reclaim_by_same_owner_is_idempotent(self, engine: object) -> None:
        app = _build_app(engine)
        async with _client(app) as client:
            first = await client.post("/api/v1/identity/owner-bootstrap", headers=_AUTH)
            second = await client.post("/api/v1/identity/owner-bootstrap", headers=_AUTH)
        assert first.status_code == 200
        assert second.status_code == 200  # same local user re-claims harmlessly
        assert second.json()["status"] == BOOTSTRAP_CLOSED


@pytest.mark.asyncio
class TestOwnerBootstrapMultiUser:
    """Different users via auth override: second claimant is denied once closed."""

    async def _seed_users(self, engine: object) -> tuple[User, User]:
        maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]
        async with maker() as session:
            alice = User(clerk_user_id="alice", email="alice@example.com", name="Alice")
            bob = User(clerk_user_id="bob", email="bob@example.com", name="Bob")
            session.add(alice)
            session.add(bob)
            await session.commit()
            await session.refresh(alice)
            await session.refresh(bob)
            return alice, bob

    async def test_second_user_forbidden_after_close(self, engine: object) -> None:
        alice, bob = await self._seed_users(engine)

        def _as(user: User) -> object:
            async def _override() -> AuthContext:
                return AuthContext(actor_type="user", user=user)

            return _override

        # Alice claims ownership.
        app_a = _build_app(engine, auth_override=_as(alice))
        async with _client(app_a) as client:
            resp = await client.post("/api/v1/identity/owner-bootstrap")
            assert resp.status_code == 200

        # Bob now tries — bootstrap is closed; typed forbidden envelope.
        app_b = _build_app(engine, auth_override=_as(bob))
        async with _client(app_b) as client:
            resp = await client.post("/api/v1/identity/owner-bootstrap")
            assert resp.status_code == 403
            body = resp.json()
            assert body["code"] == "forbidden"
            assert body["retryable"] is False
            assert "trace_id" in body

            me = (await client.get("/api/v1/identity/me")).json()
            assert ROLE_OWNER not in me["roles"]


@pytest.mark.asyncio
async def test_ensure_system_roles_idempotent(engine: object) -> None:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]
    async with maker() as session:
        await ensure_system_roles(session)
        await ensure_system_roles(session)  # second run must not duplicate
        await session.commit()
        user = User(clerk_user_id="c", email="c@example.com", name="C")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        names = await user_role_names(session, user.id)
        assert names == frozenset()  # no roles until assigned
    # All seven system roles exist exactly once.
    from sqlmodel import func, select

    from app.models.identity import Role

    async with maker() as session:
        count = (await session.exec(select(func.count()).select_from(Role))).one()
        assert count == len(SYSTEM_ROLES)
