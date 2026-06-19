"""Channel-identity mapping, lookup, and actor resolution.

Normative basis: `05-OPERATIONS-AND-SECURITY.md` §3.3 and AGENTS.md I-09. A Hermes
platform user/chat is mapped to an Ecom-OS user; an **unmapped sender has no row and
therefore no privileged identity**. The effective role is **re-resolved from the mapped
user at invocation time** (never trusted from a cached transcript snapshot); the stored
``role_snapshot`` is informational only. Revoking a mapping removes future tool access
without deleting Hermes history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from app.auth.roles import user_permission_keys, user_role_names
from app.core.context import ActorContext, ActorType
from app.core.ids import uuid7
from app.core.time import utcnow
from app.models.identity import (
    IDENTITY_STATUS_ACTIVE,
    IDENTITY_STATUS_REVOKED,
    ChannelIdentity,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession

__all__ = [
    "map_channel_identity",
    "lookup_active_channel_identity",
    "revoke_channel_identity",
    "resolve_channel_actor",
]


async def map_channel_identity(
    session: AsyncSession,
    *,
    user_id: UUID,
    platform: str,
    platform_user_id: str,
    platform_account: str = "",
    chat_id: str | None = None,
    channel_id: str | None = None,
    hermes_profile_id: str | None = None,
) -> ChannelIdentity:
    """Create (verify) a channel→user mapping."""
    identity = ChannelIdentity(
        id=uuid7(),
        user_id=user_id,
        platform=platform,
        platform_account=platform_account,
        platform_user_id=platform_user_id,
        chat_id=chat_id,
        channel_id=channel_id,
        hermes_profile_id=hermes_profile_id,
        status=IDENTITY_STATUS_ACTIVE,
        verified_at=utcnow(),
    )
    session.add(identity)
    await session.flush()
    return identity


async def lookup_active_channel_identity(
    session: AsyncSession,
    *,
    platform: str,
    platform_user_id: str,
    platform_account: str = "",
) -> ChannelIdentity | None:
    """Return the active mapping for a platform sender, or ``None`` if unmapped/revoked."""
    result = await session.exec(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_account == platform_account,
            ChannelIdentity.platform_user_id == platform_user_id,
            ChannelIdentity.status == IDENTITY_STATUS_ACTIVE,
        ),
    )
    return result.first()


async def revoke_channel_identity(session: AsyncSession, identity: ChannelIdentity) -> None:
    """Revoke a channel mapping (future tool access only; Hermes history untouched)."""
    identity.status = IDENTITY_STATUS_REVOKED
    session.add(identity)
    await session.flush()


async def resolve_channel_actor(
    session: AsyncSession,
    identity: ChannelIdentity,
) -> ActorContext:
    """Resolve the effective actor for a channel mapping, re-reading roles now."""
    roles = await user_role_names(session, identity.user_id)
    scopes = await user_permission_keys(session, identity.user_id)
    return ActorContext(
        actor_type=ActorType.CHANNEL,
        actor_id=str(identity.id),
        roles=roles,
        scopes=scopes,
        user_id=identity.user_id,
        channel_identity_id=identity.id,
    )
