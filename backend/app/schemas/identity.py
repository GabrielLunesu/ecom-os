"""API contracts for the identity surface (owner bootstrap, current actor)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.core.context import ActorType

__all__ = ["BootstrapStatus", "OwnerClaimResult", "ActorView"]


class BootstrapStatus(BaseModel):
    """Current owner-bootstrap gate state."""

    status: str = Field(description="'open' until ownership is claimed, then 'closed'.")
    is_open: bool
    is_owner: bool = Field(description="Whether the current caller is the instance owner.")


class OwnerClaimResult(BaseModel):
    """Result of a successful owner-bootstrap claim."""

    user_id: UUID
    role: str
    status: str


class ActorView(BaseModel):
    """The authenticated actor's effective identity, roles, and permissions."""

    actor_type: ActorType
    actor_id: str
    user_id: UUID | None = None
    roles: list[str]
    scopes: list[str]
