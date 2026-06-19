"""Service-identity issuance, verification, rotation, and revocation.

Normative basis: `05-OPERATIONS-AND-SECURITY.md` §3.4 — separate, audience-scoped,
rotatable machine identities; "shared all-powerful machine tokens are prohibited". The
plaintext token is returned only at issue/rotation; storage keeps a public selector and
the verifier hash (AGENTS.md I-15).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from sqlmodel import select

from app.auth.service_tokens import issue_token, split_token, verify_verifier
from app.core.context import ActorContext, ActorType
from app.core.ids import uuid7
from app.core.time import utcnow
from app.models.identity import (
    IDENTITY_STATUS_ACTIVE,
    IDENTITY_STATUS_REVOKED,
    ServiceIdentity,
)

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

__all__ = [
    "create_service_identity",
    "verify_service_token",
    "rotate_service_token",
    "revoke_service_identity",
    "service_actor_context",
]


async def create_service_identity(
    session: AsyncSession,
    *,
    name: str,
    audience: str,
    scopes: Iterable[str],
) -> tuple[ServiceIdentity, str]:
    """Create a service identity; return it and its plaintext token (shown once)."""
    issued = issue_token()
    identity = ServiceIdentity(
        id=uuid7(),
        name=name,
        audience=audience,
        scopes=" ".join(sorted(set(scopes))),
        token_selector=issued.selector,
        token_hash=issued.verifier_hash,
        status=IDENTITY_STATUS_ACTIVE,
    )
    session.add(identity)
    await session.flush()
    return identity, issued.token


async def verify_service_token(session: AsyncSession, token: str) -> ServiceIdentity | None:
    """Verify a presented service token; return the active identity or ``None``.

    O(1) lookup by public selector, then constant-time verifier check. A revoked or
    unknown identity, or a bad verifier, yields ``None`` (no privileged identity).
    """
    parts = split_token(token)
    if parts is None:
        return None
    selector, verifier = parts
    result = await session.exec(
        select(ServiceIdentity).where(ServiceIdentity.token_selector == selector),
    )
    identity = result.first()
    if identity is None or identity.status != IDENTITY_STATUS_ACTIVE:
        return None
    if not verify_verifier(verifier, identity.token_hash):
        return None
    identity.last_used_at = utcnow()
    session.add(identity)
    await session.flush()
    return identity


async def rotate_service_token(session: AsyncSession, identity: ServiceIdentity) -> str:
    """Rotate an identity's token; invalidates the old token and returns the new one."""
    issued = issue_token()
    identity.token_selector = issued.selector
    identity.token_hash = issued.verifier_hash
    identity.rotated_at = utcnow()
    session.add(identity)
    await session.flush()
    return issued.token


async def revoke_service_identity(session: AsyncSession, identity: ServiceIdentity) -> None:
    """Revoke a service identity so its token no longer authenticates."""
    identity.status = IDENTITY_STATUS_REVOKED
    identity.revoked_at = utcnow()
    session.add(identity)
    await session.flush()


def service_actor_context(identity: ServiceIdentity) -> ActorContext:
    """Build the :class:`ActorContext` for an authenticated service identity."""
    return ActorContext(
        actor_type=ActorType.SERVICE,
        actor_id=str(identity.id),
        scopes=identity.scope_set,
        service_identity_id=identity.id,
    )
