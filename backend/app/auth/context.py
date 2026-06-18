"""Request-context resolution dependency.

Builds a :class:`~app.core.context.RequestContext` from the correlation ids that the
outermost middleware (:class:`app.core.error_handling.RequestIdMiddleware`) placed on
``request.state``. This is intentionally DB-free: the authenticated actor is attached
by the identity layer via :meth:`RequestContext.model_copy` once resolved, so any
router or background entrypoint can obtain correlation context without a session.
"""

from __future__ import annotations

from fastapi import Request

from app.core.context import ActorContext, RequestContext, StoreScope

__all__ = [
    "ActorContext",
    "StoreScope",
    "RequestContext",
    "request_context_from_request",
    "get_request_context",
]


def request_context_from_request(request: Request) -> RequestContext:
    """Build a :class:`RequestContext` from ``request.state`` correlation ids.

    The middleware always sets ``request_id``/``trace_id``/``span_id``; if a caller
    constructs a request without it (e.g. a unit test), sensible empty-safe defaults
    keep this total rather than raising.
    """
    state = request.state
    request_id = getattr(state, "request_id", "") or ""
    trace_id = getattr(state, "trace_id", "") or ""
    span_id = getattr(state, "span_id", "") or ""
    parent_span_id = getattr(state, "parent_span_id", None)
    return RequestContext(
        request_id=request_id,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
    )


async def get_request_context(request: Request) -> RequestContext:
    """FastAPI dependency yielding the per-request correlation context."""
    return request_context_from_request(request)
