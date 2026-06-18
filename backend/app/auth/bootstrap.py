"""Owner bootstrap: the first owner claims the instance, then it closes.

Normative basis: `05-OPERATIONS-AND-SECURITY.md` §3.1 — "The first user becomes
``owner`` through an explicit bootstrap flow. Bootstrap closes after ownership is
established and can only be re-opened from the host with a recovery command." Build
Spec Slice 1 acceptance: "bootstrap closes after owner creation."

Server-side enforcement only: the HTTP layer requires authentication (an anonymous
caller can never reach :func:`claim_owner`), and once closed this function refuses to
grant ownership to anyone but the established owner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from app.auth.audit import AuditEvent, get_audit_sink
from app.auth.roles import assign_role, ensure_system_roles
from app.core.errors import ApiError, ErrorCode
from app.core.ids import uuid7
from app.core.time import utcnow
from app.models.identity import (
    BOOTSTRAP_CLOSED,
    BOOTSTRAP_OPEN,
    ROLE_OWNER,
    PlatformBootstrap,
)

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

    from app.models.users import User

__all__ = [
    "get_or_create_bootstrap_state",
    "is_bootstrap_open",
    "claim_owner",
    "reopen_bootstrap",
]


async def get_or_create_bootstrap_state(
    session: AsyncSession,
    *,
    for_update: bool = False,
) -> PlatformBootstrap:
    """Return the singleton bootstrap row, creating it (open) if absent."""
    statement = select(PlatformBootstrap).where(PlatformBootstrap.singleton == True)  # noqa: E712
    if for_update:
        # Serializes concurrent claims on Postgres; a no-op on sqlite.
        statement = statement.with_for_update()
    result = await session.exec(statement)
    state = result.first()
    if state is None:
        state = PlatformBootstrap(id=uuid7(), singleton=True, status=BOOTSTRAP_OPEN)
        session.add(state)
        await session.flush()
    return state


async def is_bootstrap_open(session: AsyncSession) -> bool:
    """Return whether owner bootstrap is still open."""
    state = await get_or_create_bootstrap_state(session)
    return state.status == BOOTSTRAP_OPEN


async def claim_owner(
    session: AsyncSession,
    user: User,
    *,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> PlatformBootstrap:
    """Claim instance ownership for ``user`` and close bootstrap.

    Idempotent for the established owner. Raises :class:`ApiError` (``forbidden``) if
    bootstrap is closed and ``user`` is not the owner.
    """
    state = await get_or_create_bootstrap_state(session, for_update=True)

    if state.status == BOOTSTRAP_CLOSED:
        if state.owner_user_id == user.id:
            return state  # idempotent re-claim by the owner
        raise ApiError(
            ErrorCode.FORBIDDEN,
            "Owner bootstrap is closed.",
            remediation="Ownership is already established; ask the owner for access.",
        )

    await ensure_system_roles(session)
    await assign_role(session, user_id=user.id, role_name=ROLE_OWNER)

    state.status = BOOTSTRAP_CLOSED
    state.owner_user_id = user.id
    state.closed_at = utcnow()
    session.add(state)
    await session.flush()

    await get_audit_sink().record(
        AuditEvent(
            action="owner.bootstrap",
            actor_id=str(user.id),
            target=str(user.id),
            details={"role": ROLE_OWNER},
            trace_id=trace_id,
            request_id=request_id,
        ),
    )
    await session.commit()
    return state


async def reopen_bootstrap(session: AsyncSession, *, reason: str) -> PlatformBootstrap:
    """Host-only recovery: re-open bootstrap (not reachable via the HTTP API).

    Intended to be invoked from a host shell/management command, never an
    authenticated browser route, matching the "re-opened from the host" requirement.
    """
    state = await get_or_create_bootstrap_state(session, for_update=True)
    state.status = BOOTSTRAP_OPEN
    state.owner_user_id = None
    state.closed_at = None
    state.opened_at = utcnow()
    session.add(state)
    await session.flush()
    await get_audit_sink().record(
        AuditEvent(action="owner.bootstrap.reopen", details={"reason": reason}),
    )
    await session.commit()
    return state
