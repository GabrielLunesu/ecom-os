"""Deterministic identity fixtures for tests and local seeding.

Provides one owner, one admin, one viewer (human roles), one active service identity,
and one active channel mapping plus an explicitly-unmapped sender — enough to exercise
both allowed and denied paths across role, service, and channel identity. Reusable by
other domains' tests so they do not re-invent identity seeding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.auth.channel_identity import map_channel_identity
from app.auth.roles import assign_role, ensure_system_roles
from app.auth.service_identity import create_service_identity
from app.models.identity import (
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_VIEWER,
    ChannelIdentity,
    ServiceIdentity,
)
from app.models.users import User

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

__all__ = ["IdentityFixtures", "seed_identity_fixtures"]


@dataclass
class IdentityFixtures:
    """Handles to the seeded identity records and the service plaintext token."""

    owner: User
    admin: User
    viewer: User
    service: ServiceIdentity
    service_token: str
    channel: ChannelIdentity
    # An explicitly unmapped sender (no channel identity row exists for it).
    unmapped_platform: str = "telegram"
    unmapped_platform_user_id: str = "unmapped-sender-999"


async def _make_user(session: AsyncSession, key: str) -> User:
    user = User(clerk_user_id=key, email=f"{key}@example.com", name=key.title())
    session.add(user)
    await session.flush()
    return user


async def seed_identity_fixtures(session: AsyncSession) -> IdentityFixtures:
    """Seed roles and a representative set of human/service/channel identities."""
    await ensure_system_roles(session)

    owner = await _make_user(session, "owner")
    admin = await _make_user(session, "admin")
    viewer = await _make_user(session, "viewer")
    await assign_role(session, user_id=owner.id, role_name=ROLE_OWNER)
    await assign_role(session, user_id=admin.id, role_name=ROLE_ADMIN)
    await assign_role(session, user_id=viewer.id, role_name=ROLE_VIEWER)

    service, token = await create_service_identity(
        session,
        name="hermes-adapter",
        audience="hermes-adapter",
        scopes=["identity:read"],
    )

    channel = await map_channel_identity(
        session,
        user_id=admin.id,
        platform="telegram",
        platform_user_id="tg-admin-1",
        platform_account="bot-1",
    )
    await session.commit()
    return IdentityFixtures(
        owner=owner,
        admin=admin,
        viewer=viewer,
        service=service,
        service_token=token,
        channel=channel,
    )
