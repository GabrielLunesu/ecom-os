"""OpenClawCompatTransport — LEGACY/DEV compatibility transport (DR-A03-01).

Adapts the in-repo OpenClaw WebSocket JSON-RPC gateway (`app/services/openclaw`) to the
``HermesBridge`` interface so the dashboard can be developed locally before a real pinned
Hermes endpoint exists. This is explicitly a **compatibility / development** transport:

- It is NOT the Hermes runtime. Real-Hermes conformance stays BLOCKED until a genuine Hermes
  v0.16.0 endpoint is provided (use ``HermesNativeTransport`` for that boundary).
- Streaming is **degraded**: OpenClaw `chat.send` is request/response, so ``submit_prompt``
  yields a single final message rather than token deltas. Background runs and branch are not
  mapped here; use the native transport or fixtures.

RPC callables are injected so this is unit-testable without a live gateway.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import uuid4

from app.services.openclaw.gateway_rpc import (
    GatewayConfig,
    ensure_session,
    get_chat_history,
    openclaw_call,
    send_message,
)

from .types import (
    BackgroundRunRequest,
    BranchRequest,
    CreateSession,
    HermesCapabilities,
    HermesEvent,
    HermesEventType,
    HermesHealth,
    HermesHistory,
    HermesMessage,
    HermesRunRef,
    HermesRunStatus,
    HermesSessionRef,
    HermesSessionStatus,
    InteractivePrompt,
    InterruptRequest,
    Page,
    SessionQuery,
    SessionState,
)

# Capability flags the compat transport can honestly claim (interactive, non-streaming).
_COMPAT_FLAGS = frozenset(
    {
        "interactive.json_rpc",
        "interactive.session_create",
        "interactive.session_resume",
        "interactive.session_history",
        "interactive.interrupt",
    }
)


class CompatUnsupported(NotImplementedError):
    """The requested operation is not supported by the OpenClaw compat transport."""


def _as_messages(history: object) -> tuple[HermesMessage, ...]:
    """Best-effort parse of an OpenClaw chat.history payload into typed messages."""
    rows: list[dict[str, Any]] = []
    if isinstance(history, dict):
        raw = history.get("messages") or history.get("history") or []
        if isinstance(raw, list):
            rows = [r for r in raw if isinstance(r, dict)]
    elif isinstance(history, list):
        rows = [r for r in history if isinstance(r, dict)]
    out: list[HermesMessage] = []
    for row in rows:
        role = str(row.get("role") or row.get("author") or "assistant")
        text = str(row.get("text") or row.get("content") or row.get("message") or "")
        out.append(HermesMessage(role=role, text=text))
    return tuple(out)


class OpenClawCompatTransport:
    """A ``HermesBridge`` over the OpenClaw gateway — compatibility/dev only."""

    transport_label = "openclaw-compat"

    def __init__(
        self,
        config: GatewayConfig,
        *,
        profile_id: str = "openclaw",
        ensure_session_fn: Callable[..., Awaitable[Any]] = ensure_session,
        history_fn: Callable[..., Awaitable[Any]] = get_chat_history,
        send_fn: Callable[..., Awaitable[Any]] = send_message,
        call_fn: Callable[..., Awaitable[Any]] = openclaw_call,
    ) -> None:
        self._config = config
        self._profile_id = profile_id
        self._ensure = ensure_session_fn
        self._history = history_fn
        self._send = send_fn
        self._call = call_fn

    # --- capability + health ---
    async def probe(self) -> HermesCapabilities:
        return HermesCapabilities(flags=_COMPAT_FLAGS)

    async def health(self) -> HermesHealth:
        return HermesHealth(
            ok=True,
            profile_id=self._profile_id,
            detail="openclaw compatibility transport (NOT real Hermes)",
        )

    # --- interactive sessions ---
    async def create_session(self, request: CreateSession) -> HermesSessionRef:
        session_key = request.resume_session_id or f"ecom-chat-{uuid4().hex[:12]}"
        await self._ensure(session_key, config=self._config, label=request.title)
        return HermesSessionRef(
            profile_id=self._profile_id, session_id=session_key, source=request.source
        )

    async def list_sessions(self, query: SessionQuery) -> Page:
        result = await self._call("sessions.list", {}, config=self._config)
        items: list[Any] = []
        if isinstance(result, dict):
            raw = result.get("sessions") or result.get("items") or []
            if isinstance(raw, list):
                items = raw
        summaries = tuple(
            HermesSessionRef(profile_id=self._profile_id, session_id=str(s.get("key")))
            for s in items
            if isinstance(s, dict) and s.get("key")
        )
        from .types import HermesSessionSummary

        return Page(
            items=tuple(
                HermesSessionSummary(ref=ref, title=None, last_seen=None) for ref in summaries
            )
        )

    async def get_history(self, ref: HermesSessionRef) -> HermesHistory:
        raw = await self._history(ref.session_id, self._config)
        return HermesHistory(ref=ref, messages=_as_messages(raw), source="openclaw")

    async def get_status(self, ref: HermesSessionRef) -> HermesSessionStatus:
        # OpenClaw does not expose a clean per-session run state here; report unknown
        # rather than inventing one.
        return HermesSessionStatus(ref=ref, state=SessionState.unknown)

    async def submit_prompt(self, request: InteractivePrompt) -> AsyncIterator[HermesEvent]:
        result = await self._send(
            request.text, session_key=request.ref.session_id, config=self._config
        )
        # Degraded streaming: one final message, then terminal.
        yield HermesEvent(
            type=HermesEventType.message_final,
            seq=0,
            payload={"result": result},
        )
        yield HermesEvent(type=HermesEventType.final, seq=1, payload={})

    async def interrupt(self, request: InterruptRequest) -> None:
        await self._call("chat.abort", {"sessionKey": request.ref.session_id}, config=self._config)

    async def branch(self, request: BranchRequest) -> HermesSessionRef:
        raise CompatUnsupported("branch is not supported by the OpenClaw compat transport")

    # --- background runs: not mapped in compat ---
    async def start_run(self, request: BackgroundRunRequest) -> HermesRunRef:
        raise CompatUnsupported("background runs require the native Hermes transport")

    async def stream_run(self, ref: HermesRunRef) -> AsyncIterator[HermesEvent]:
        raise CompatUnsupported("background runs require the native Hermes transport")
        yield  # pragma: no cover - makes this an async generator

    async def get_run(self, ref: HermesRunRef) -> HermesRunStatus:
        raise CompatUnsupported("background runs require the native Hermes transport")

    async def stop_run(self, ref: HermesRunRef) -> None:
        raise CompatUnsupported("background runs require the native Hermes transport")
