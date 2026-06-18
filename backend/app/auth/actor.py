"""Resolve the authenticated v2 :class:`ActorContext` and enforce permissions.

Bridges the prototype auth seam (:func:`app.core.auth.get_auth_context`, which yields
a human ``AuthContext``) into the v2 :class:`~app.core.context.ActorContext`, attaching
the effective instance roles/permissions resolved from the database. Authorization is
server-side and role/permission-driven; client-supplied role names are never trusted
(Runtime §6.2, AGENTS.md §7).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi import Depends, Request

from app.auth.roles import user_permission_keys, user_role_names
from app.core.auth import AuthContext, get_auth_context
from app.core.context import ActorContext, ActorType
from app.core.errors import ApiError, ErrorCode
from app.db.session import get_session

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

__all__ = ["resolve_human_actor", "get_actor_context", "require_permission", "require_role"]

AUTH_DEP = Depends(get_auth_context)
SESSION_DEP = Depends(get_session)


async def resolve_human_actor(session: AsyncSession, auth: AuthContext) -> ActorContext:
    """Build an :class:`ActorContext` for an authenticated human user."""
    if auth.user is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Not authenticated.")
    user = auth.user
    roles = await user_role_names(session, user.id)
    scopes = await user_permission_keys(session, user.id)
    return ActorContext(
        actor_type=ActorType.HUMAN,
        actor_id=str(user.id),
        roles=roles,
        scopes=scopes,
        user_id=user.id,
    )


async def get_actor_context(
    request: Request,  # noqa: ARG001 - reserved for future channel/service resolution
    auth: AuthContext = AUTH_DEP,
    session: AsyncSession = SESSION_DEP,
) -> ActorContext:
    """FastAPI dependency yielding the resolved human actor context."""
    return await resolve_human_actor(session, auth)


ACTOR_DEP = Depends(get_actor_context)


def require_permission(permission: str) -> Callable[[ActorContext], Awaitable[ActorContext]]:
    """Return a dependency that requires ``permission`` on the resolved actor."""

    async def _dep(actor: ActorContext = ACTOR_DEP) -> ActorContext:
        if not actor.has_scope(permission):
            raise ApiError(
                ErrorCode.FORBIDDEN,
                f"Missing required permission: {permission}.",
                details={"required_permission": permission},
            )
        return actor

    return _dep


def require_role(role: str) -> Callable[[ActorContext], Awaitable[ActorContext]]:
    """Return a dependency that requires instance ``role`` on the resolved actor."""

    async def _dep(actor: ActorContext = ACTOR_DEP) -> ActorContext:
        if not actor.has_role(role):
            raise ApiError(
                ErrorCode.FORBIDDEN,
                f"Requires the {role} role.",
                details={"required_role": role},
            )
        return actor

    return _dep
