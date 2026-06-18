"""Request / actor / store / trace context primitives.

Normative basis: `03-ENGINEERING.md` §6 ("Trace context propagation") and Runtime
spec §6.2 (tool-invocation context). Every request, job, event, Hermes run, tool call,
action, and connector attempt carries or creates these fields. Absent fields stay
``None`` — they are never fabricated (AGENTS.md I-09, I-12).

These types are dependency-light on purpose (stdlib + pydantic only) so any layer can
import them without pulling in models, the DB, or auth. The richer authenticated actor
is re-exported from :mod:`app.auth.context` for callers that prefer that path.
"""

from __future__ import annotations

import os
import re
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

__all__ = [
    "ActorType",
    "StoreScope",
    "ActorContext",
    "RequestContext",
    "new_trace_id",
    "new_span_id",
    "parse_traceparent",
    "format_traceparent",
]

# W3C Trace Context: "00-<32 hex trace-id>-<16 hex span-id>-<2 hex flags>".
_TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$",
)
_ALL_ZERO_TRACE = "0" * 32
_ALL_ZERO_SPAN = "0" * 16


def new_trace_id() -> str:
    """Return a fresh 16-byte (32 hex) W3C trace id."""
    return os.urandom(16).hex()


def new_span_id() -> str:
    """Return a fresh 8-byte (16 hex) W3C span id."""
    return os.urandom(8).hex()


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    """Parse a ``traceparent`` header into ``(trace_id, parent_span_id)``.

    Returns ``None`` for absent/malformed headers or the all-zero (invalid) ids, so a
    caller can mint a fresh trace instead of trusting a bad upstream value.
    """
    if not value:
        return None
    match = _TRACEPARENT_RE.match(value.strip().lower())
    if match is None:
        return None
    trace_id = match.group("trace_id")
    span_id = match.group("span_id")
    if trace_id == _ALL_ZERO_TRACE or span_id == _ALL_ZERO_SPAN:
        return None
    return trace_id, span_id


def format_traceparent(trace_id: str, span_id: str, *, sampled: bool = True) -> str:
    """Build a ``traceparent`` header value for outbound propagation."""
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"


class ActorType(str, Enum):
    """The kind of authenticated principal behind a request.

    Mirrors the identity model: humans (`05-OPS` §3.1), service identities (§3.4),
    and channel identities (§3.3). ``system`` is for internal startup/migration tasks.
    """

    HUMAN = "human"
    SERVICE = "service"
    CHANNEL = "channel"
    SYSTEM = "system"


class StoreScope(BaseModel):
    """Exact store/brand binding for a scoped operation (AGENTS.md I-09).

    "Default", "latest", or "most recently connected" selection is forbidden; a write
    must name its store explicitly, so this carries the resolved ids only.
    """

    model_config = ConfigDict(frozen=True)

    store_id: UUID
    brand_id: UUID | None = None


class ActorContext(BaseModel):
    """The authenticated principal and its effective roles/scopes.

    Resolved server-side from the auth layer; never trusted from client-supplied role
    names (Runtime §6.2). ``roles``/``scopes`` are the effective, re-resolved sets.
    """

    model_config = ConfigDict(frozen=True)

    actor_type: ActorType
    actor_id: str
    roles: frozenset[str] = frozenset()
    scopes: frozenset[str] = frozenset()
    user_id: UUID | None = None
    service_identity_id: UUID | None = None
    channel_identity_id: UUID | None = None
    store_scope: StoreScope | None = None

    def has_role(self, role: str) -> bool:
        """Return whether the actor holds ``role``."""
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        """Return whether the actor holds ``scope``."""
        return scope in self.scopes


class RequestContext(BaseModel):
    """Correlation + identity context attached to a single request.

    Field set follows `03-ENGINEERING.md` §6. Hermes fields are populated only when a
    request originates from / is linked to a Hermes run; otherwise they stay ``None``.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    actor: ActorContext | None = None
    store_id: UUID | None = None
    hermes_profile_id: str | None = None
    hermes_session_id: str | None = None
    hermes_turn_id: str | None = None
