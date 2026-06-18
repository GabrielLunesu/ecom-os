"""A01 foundation: request/actor/store context + W3C trace propagation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.context import RequestContext, get_request_context
from app.core.context import (
    ActorContext,
    ActorType,
    StoreScope,
    format_traceparent,
    new_span_id,
    new_trace_id,
    parse_traceparent,
)
from app.core.error_handling import install_error_handling


class TestTraceparent:
    def test_roundtrip(self) -> None:
        trace_id = new_trace_id()
        span_id = new_span_id()
        header = format_traceparent(trace_id, span_id)
        assert parse_traceparent(header) == (trace_id, span_id)

    def test_lengths(self) -> None:
        assert len(new_trace_id()) == 32  # noqa: PLR2004
        assert len(new_span_id()) == 16  # noqa: PLR2004

    @pytest.mark.parametrize(
        "value",
        [
            None,
            "",
            "garbage",
            "00-tooshort-tooshort-00",
            f"00-{'0' * 32}-{'a' * 16}-01",  # all-zero trace id is invalid
            f"00-{'a' * 32}-{'0' * 16}-01",  # all-zero span id is invalid
        ],
    )
    def test_invalid_values_rejected(self, value: str | None) -> None:
        assert parse_traceparent(value) is None


class TestActorContext:
    def test_roles_and_scopes(self) -> None:
        actor = ActorContext(
            actor_type=ActorType.HUMAN,
            actor_id="u1",
            roles=frozenset({"owner"}),
            scopes=frozenset({"identity:write"}),
        )
        assert actor.has_role("owner")
        assert not actor.has_role("viewer")
        assert actor.has_scope("identity:write")

    def test_store_scope_binding(self) -> None:
        store = uuid4()
        scope = StoreScope(store_id=store)
        actor = ActorContext(
            actor_type=ActorType.SERVICE,
            actor_id="svc",
            store_scope=scope,
        )
        assert actor.store_scope is not None
        assert actor.store_scope.store_id == store

    def test_frozen(self) -> None:
        actor = ActorContext(actor_type=ActorType.HUMAN, actor_id="u1")
        with pytest.raises(Exception):  # noqa: B017,PT011 - pydantic frozen
            actor.actor_id = "u2"  # type: ignore[misc]


def _trace_app() -> FastAPI:
    app = FastAPI()
    install_error_handling(app)

    @app.get("/_ctx")
    async def _ctx(ctx: RequestContext = Depends(get_request_context)) -> dict[str, str | None]:
        return {
            "request_id": ctx.request_id,
            "trace_id": ctx.trace_id,
            "span_id": ctx.span_id,
            "parent_span_id": ctx.parent_span_id,
        }

    return app


@pytest.mark.asyncio
class TestTracePropagationMiddleware:
    async def _client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=_trace_app()), base_url="http://t")

    async def test_fresh_trace_when_no_header(self) -> None:
        async with await self._client() as client:
            resp = await client.get("/_ctx")
        assert resp.status_code == 200  # noqa: PLR2004
        body = resp.json()
        assert len(body["trace_id"]) == 32  # noqa: PLR2004
        assert body["parent_span_id"] is None
        assert resp.headers["x-trace-id"] == body["trace_id"]
        assert resp.headers["traceparent"].startswith(f"00-{body['trace_id']}-")

    async def test_continues_inbound_trace(self) -> None:
        trace_id = new_trace_id()
        parent_span = new_span_id()
        traceparent = format_traceparent(trace_id, parent_span)
        async with await self._client() as client:
            resp = await client.get("/_ctx", headers={"traceparent": traceparent})
        body = resp.json()
        assert body["trace_id"] == trace_id
        assert body["parent_span_id"] == parent_span
        assert body["span_id"] != parent_span  # server mints its own span

    async def test_malformed_inbound_starts_fresh(self) -> None:
        async with await self._client() as client:
            resp = await client.get("/_ctx", headers={"traceparent": "garbage"})
        body = resp.json()
        assert len(body["trace_id"]) == 32  # noqa: PLR2004
        assert body["parent_span_id"] is None
