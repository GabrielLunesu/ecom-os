"""A01 foundation: service & channel identity verification + role enforcement.

Covers allowed and denied paths for role, service, and channel identities, plus the
I-09 rule that a channel actor's effective role is re-resolved at invocation time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.actor import require_permission, require_role
from app.auth.channel_identity import (
    lookup_active_channel_identity,
    resolve_channel_actor,
    revoke_channel_identity,
)
from app.auth.fixtures import seed_identity_fixtures
from app.auth.roles import assign_role
from app.auth.service_identity import (
    revoke_service_identity,
    rotate_service_token,
    service_actor_context,
    verify_service_token,
)
from app.core.context import ActorType
from app.core.errors import ApiError, ErrorCode
from app.models.identity import ROLE_OWNER


@pytest_asyncio.fixture
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'enf.db'}")
    async with engine.connect() as conn, conn.begin():
        await conn.run_sync(SQLModel.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
class TestServiceIdentity:
    async def test_valid_token_resolves_active_identity(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        identity = await verify_service_token(session, fx.service_token)
        assert identity is not None
        assert identity.id == fx.service.id
        actor = service_actor_context(identity)
        assert actor.actor_type is ActorType.SERVICE
        assert actor.has_scope("identity:read")

    async def test_malformed_and_unknown_tokens_denied(self, session: AsyncSession) -> None:
        await seed_identity_fixtures(session)
        assert await verify_service_token(session, "no-separator") is None
        assert await verify_service_token(session, "selector.wrongverifier") is None

    async def test_tampered_verifier_denied(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        selector, _, _verifier = fx.service_token.partition(".")
        assert await verify_service_token(session, f"{selector}.tampered") is None

    async def test_revoked_identity_denied(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        await revoke_service_identity(session, fx.service)
        await session.commit()
        assert await verify_service_token(session, fx.service_token) is None

    async def test_rotation_invalidates_old_token(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        new_token = await rotate_service_token(session, fx.service)
        await session.commit()
        assert await verify_service_token(session, fx.service_token) is None
        assert await verify_service_token(session, new_token) is not None


@pytest.mark.asyncio
class TestChannelIdentity:
    async def test_mapped_sender_resolves_actor(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        mapping = await lookup_active_channel_identity(
            session,
            platform="telegram",
            platform_user_id="tg-admin-1",
            platform_account="bot-1",
        )
        assert mapping is not None
        actor = await resolve_channel_actor(session, mapping)
        assert actor.actor_type is ActorType.CHANNEL
        assert actor.user_id == fx.admin.id
        assert "admin" in actor.roles

    async def test_unmapped_sender_has_no_identity(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        mapping = await lookup_active_channel_identity(
            session,
            platform=fx.unmapped_platform,
            platform_user_id=fx.unmapped_platform_user_id,
        )
        assert mapping is None  # no privileged identity by inference (I-09)

    async def test_revoked_mapping_denied(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        await revoke_channel_identity(session, fx.channel)
        await session.commit()
        mapping = await lookup_active_channel_identity(
            session,
            platform="telegram",
            platform_user_id="tg-admin-1",
            platform_account="bot-1",
        )
        assert mapping is None

    async def test_effective_role_reresolved_at_invocation(self, session: AsyncSession) -> None:
        # I-09: a new grant to the mapped user is reflected immediately, not cached.
        fx = await seed_identity_fixtures(session)
        await assign_role(session, user_id=fx.admin.id, role_name=ROLE_OWNER)
        await session.commit()
        actor = await resolve_channel_actor(session, fx.channel)
        assert "owner" in actor.roles


@pytest.mark.asyncio
class TestRoleEnforcement:
    async def test_permission_allowed_and_denied(self, session: AsyncSession) -> None:
        fx = await seed_identity_fixtures(session)
        from app.core.context import ActorContext

        owner_actor = ActorContext(
            actor_type=ActorType.HUMAN,
            actor_id=str(fx.owner.id),
            roles=frozenset({"owner"}),
            scopes=frozenset({"identity:write"}),
            user_id=fx.owner.id,
        )
        viewer_actor = ActorContext(
            actor_type=ActorType.HUMAN,
            actor_id=str(fx.viewer.id),
            roles=frozenset({"viewer"}),
            scopes=frozenset(),
            user_id=fx.viewer.id,
        )

        allow = require_permission("identity:write")
        assert (await allow(owner_actor)) is owner_actor
        with pytest.raises(ApiError) as exc:
            await allow(viewer_actor)
        assert exc.value.code is ErrorCode.FORBIDDEN

    async def test_role_required(self, session: AsyncSession) -> None:
        from app.core.context import ActorContext

        admin_actor = ActorContext(
            actor_type=ActorType.HUMAN,
            actor_id="a",
            roles=frozenset({"admin"}),
        )
        need_owner = require_role("owner")
        with pytest.raises(ApiError):
            await need_owner(admin_actor)
