"""Identity API: current actor and owner bootstrap.

All routes require authentication server-side (the auth dependency rejects anonymous
callers with 401), and every error is the typed :class:`ErrorEnvelope`. This is the
first real endpoint set built entirely on the A01 foundation contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request

from app.auth.actor import get_actor_context
from app.auth.bootstrap import claim_owner, get_or_create_bootstrap_state
from app.core.auth import AuthContext, get_auth_context
from app.core.context import ActorContext
from app.core.errors import ApiError, ErrorCode, ErrorEnvelope
from app.db.session import get_session
from app.models.identity import BOOTSTRAP_OPEN, ROLE_OWNER
from app.schemas.identity import ActorView, BootstrapStatus, OwnerClaimResult

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/identity", tags=["identity"])

_AUTH_DEP = Depends(get_auth_context)
_ACTOR_DEP = Depends(get_actor_context)
_SESSION_DEP = Depends(get_session)

_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorEnvelope, "description": "Caller is not authenticated."},
    403: {"model": ErrorEnvelope, "description": "Caller lacks the required privilege."},
}


@router.get(
    "/me",
    response_model=ActorView,
    summary="Current actor",
    description="Return the authenticated actor's effective identity, roles, and permissions.",
    responses=_ERROR_RESPONSES,
)
async def get_me(actor: ActorContext = _ACTOR_DEP) -> ActorView:
    """Return the resolved actor context for the current caller."""
    return ActorView(
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        user_id=actor.user_id,
        roles=sorted(actor.roles),
        scopes=sorted(actor.scopes),
    )


@router.get(
    "/bootstrap-status",
    response_model=BootstrapStatus,
    summary="Owner bootstrap status",
    responses=_ERROR_RESPONSES,
)
async def bootstrap_status(
    auth: AuthContext = _AUTH_DEP,
    session: AsyncSession = _SESSION_DEP,
) -> BootstrapStatus:
    """Report whether owner bootstrap is open and whether the caller is the owner."""
    state = await get_or_create_bootstrap_state(session)
    await session.commit()
    is_owner = auth.user is not None and state.owner_user_id == auth.user.id
    return BootstrapStatus(
        status=state.status,
        is_open=state.status == BOOTSTRAP_OPEN,
        is_owner=is_owner,
    )


@router.post(
    "/owner-bootstrap",
    response_model=OwnerClaimResult,
    summary="Claim instance ownership",
    description=(
        "Claim ownership of a freshly-installed instance. Succeeds only while bootstrap "
        "is open; closes it on success. Idempotent for the established owner; forbidden "
        "for anyone else once closed."
    ),
    responses=_ERROR_RESPONSES,
)
async def owner_bootstrap(
    request: Request,
    auth: AuthContext = _AUTH_DEP,
    session: AsyncSession = _SESSION_DEP,
) -> OwnerClaimResult:
    """Claim ownership for the authenticated caller and close bootstrap."""
    if auth.user is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Not authenticated.")
    state = await claim_owner(
        session,
        auth.user,
        trace_id=getattr(request.state, "trace_id", None),
        request_id=getattr(request.state, "request_id", None),
    )
    return OwnerClaimResult(
        user_id=auth.user.id,
        role=ROLE_OWNER,
        status=state.status,
    )
