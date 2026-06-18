"""A01-owned authentication, identity, and request-context surface.

This package is the stable seam other domains (A02–A09) consume:

* :class:`app.core.context.ActorContext` / :class:`~app.core.context.StoreScope` —
  re-exported here from their dependency-light home.
* :func:`get_request_context` — the FastAPI dependency that yields the per-request
  correlation + identity context.

Identity records (users, roles, service/channel identities) and owner bootstrap live
in sibling modules of this package as they land.
"""

from __future__ import annotations

from app.auth.context import get_request_context, request_context_from_request
from app.core.context import ActorContext, RequestContext, StoreScope

__all__ = [
    "ActorContext",
    "RequestContext",
    "StoreScope",
    "get_request_context",
    "request_context_from_request",
]
