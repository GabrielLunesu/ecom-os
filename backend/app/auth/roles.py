"""System role / permission seeding and user-role resolution.

Seeds the minimum instance roles (`01-ARCHITECTURE.md` §16) and a small foundation
permission set covering identity administration. This is deliberately an identity
*primitive* layer — domain agents register their own business permissions; A01 does not
encode business authorization here (a common trap called out in the handoff).

All operations are idempotent so they are safe to run at bootstrap and on restart.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import col, select

from app.core.ids import uuid7
from app.core.time import utcnow
from app.models.identity import (
    ROLE_ADMIN,
    ROLE_CS_LEAD,
    ROLE_CS_REP,
    ROLE_FINANCE,
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    SYSTEM_ROLES,
    Permission,
    Role,
    RolePermission,
    UserRole,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlmodel.ext.asyncio.session import AsyncSession

__all__ = [
    "FOUNDATION_PERMISSIONS",
    "ensure_system_roles",
    "assign_role",
    "user_role_names",
    "user_permission_keys",
]

# Foundation (identity-administration) permissions. Domains add their own.
PERM_IDENTITY_READ = "identity:read"
PERM_IDENTITY_WRITE = "identity:write"
PERM_SERVICE_IDENTITY_MANAGE = "service_identity:manage"
PERM_CHANNEL_IDENTITY_MANAGE = "channel_identity:manage"
PERM_AUTONOMY_MANAGE = "autonomy:manage"

FOUNDATION_PERMISSIONS: dict[str, str] = {
    PERM_IDENTITY_READ: "View users, roles, and identities.",
    PERM_IDENTITY_WRITE: "Create/modify users, roles, and role assignments.",
    PERM_SERVICE_IDENTITY_MANAGE: "Create, rotate, and revoke service identities.",
    PERM_CHANNEL_IDENTITY_MANAGE: "Map and revoke channel identities.",
    PERM_AUTONOMY_MANAGE: "Change instance autonomy and ownership-level settings.",
}

# Role -> granted foundation permissions. owner gets everything.
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_OWNER: set(FOUNDATION_PERMISSIONS),
    ROLE_ADMIN: {
        PERM_IDENTITY_READ,
        PERM_IDENTITY_WRITE,
        PERM_SERVICE_IDENTITY_MANAGE,
        PERM_CHANNEL_IDENTITY_MANAGE,
    },
    ROLE_OPERATOR: {PERM_IDENTITY_READ},
    ROLE_CS_LEAD: {PERM_IDENTITY_READ},
    ROLE_CS_REP: {PERM_IDENTITY_READ},
    ROLE_FINANCE: {PERM_IDENTITY_READ},
    ROLE_VIEWER: set(),
}

_ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_OWNER: "Full control over all instance and autonomy settings.",
    ROLE_ADMIN: "Manage users, connections, agents, and policies except ownership transfer.",
    ROLE_OPERATOR: "Operational pages and configured approvals.",
    ROLE_CS_LEAD: "Queue ownership, escalation, and CS approvals.",
    ROLE_CS_REP: "Assigned tickets and granted actions.",
    ROLE_FINANCE: "Financial data and refund approvals.",
    ROLE_VIEWER: "Selected read-only surfaces.",
}


async def _get_role(session: AsyncSession, name: str) -> Role | None:
    result = await session.exec(select(Role).where(Role.name == name))
    return result.first()


async def _get_permission(session: AsyncSession, key: str) -> Permission | None:
    result = await session.exec(select(Permission).where(Permission.key == key))
    return result.first()


async def ensure_system_roles(session: AsyncSession) -> None:
    """Idempotently create the system roles, permissions, and their grants."""
    perms: dict[str, Permission] = {}
    for key, description in FOUNDATION_PERMISSIONS.items():
        perm = await _get_permission(session, key)
        if perm is None:
            perm = Permission(id=uuid7(), key=key, description=description)
            session.add(perm)
        perms[key] = perm
    await session.flush()

    for role_name in SYSTEM_ROLES:
        role = await _get_role(session, role_name)
        if role is None:
            role = Role(
                id=uuid7(),
                name=role_name,
                description=_ROLE_DESCRIPTIONS.get(role_name, ""),
                is_system=True,
            )
            session.add(role)
            await session.flush()
        granted = await session.exec(
            select(RolePermission.permission_id).where(RolePermission.role_id == role.id),
        )
        existing_perm_ids = set(granted.all())
        for key in _ROLE_PERMISSIONS.get(role_name, set()):
            perm = perms[key]
            if perm.id not in existing_perm_ids:
                session.add(RolePermission(id=uuid7(), role_id=role.id, permission_id=perm.id))
    await session.flush()


async def assign_role(
    session: AsyncSession,
    *,
    user_id: UUID,
    role_name: str,
    granted_by_user_id: UUID | None = None,
) -> UserRole:
    """Assign ``role_name`` to a user (idempotent); returns the assignment."""
    role = await _get_role(session, role_name)
    if role is None:
        msg = f"unknown role: {role_name}"
        raise ValueError(msg)
    existing = await session.exec(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id),
    )
    found = existing.first()
    if found is not None:
        return found
    assignment = UserRole(
        id=uuid7(),
        user_id=user_id,
        role_id=role.id,
        granted_at=utcnow(),
        granted_by_user_id=granted_by_user_id,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def user_role_names(session: AsyncSession, user_id: UUID) -> frozenset[str]:
    """Return the set of role names currently assigned to ``user_id``."""
    result = await session.exec(
        select(Role.name)
        .join(UserRole, col(UserRole.role_id) == col(Role.id))
        .where(UserRole.user_id == user_id),
    )
    return frozenset(result.all())


async def user_permission_keys(session: AsyncSession, user_id: UUID) -> frozenset[str]:
    """Return the effective permission keys for ``user_id`` across all its roles."""
    result = await session.exec(
        select(Permission.key)
        .join(RolePermission, col(RolePermission.permission_id) == col(Permission.id))
        .join(UserRole, col(UserRole.role_id) == col(RolePermission.role_id))
        .where(UserRole.user_id == user_id),
    )
    return frozenset(result.all())
