"""Tests for the OpenClaw compatibility transport (DR-A03-01: compat/dev, NOT Hermes).

Hermetic: the OpenClaw RPC callables are injected with fakes, so no live gateway is needed.
Proves the bridge interface maps onto the real OpenClaw protocol shape (sessions.patch,
chat.history, chat.send, chat.abort) and that background/branch are honestly unsupported.
"""

from __future__ import annotations

import pytest

from app.hermes.bridge import HermesBridge
from app.hermes.openclaw_compat import CompatUnsupported, OpenClawCompatTransport
from app.hermes.types import (
    BackgroundRunRequest,
    BranchRequest,
    CreateSession,
    HermesEventType,
    HermesSessionRef,
    InteractivePrompt,
    InterruptRequest,
)
from app.services.openclaw.gateway_rpc import GatewayConfig


class _RecordingRPC:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def ensure(self, key, *, config, label=None):  # type: ignore[no-untyped-def]
        self.calls.append(("ensure", {"key": key, "label": label}))
        return {"ok": True}

    async def history(self, key, config, limit=None):  # type: ignore[no-untyped-def]
        self.calls.append(("history", {"key": key}))
        return {"messages": [{"role": "user", "text": "hi"},
                             {"role": "assistant", "text": "hello"}]}

    async def send(self, message, *, session_key, config, deliver=False):  # type: ignore[no-untyped-def]
        self.calls.append(("send", {"session_key": session_key, "message": message}))
        return {"reply": "ok"}

    async def call(self, method, params=None, *, config):  # type: ignore[no-untyped-def]
        self.calls.append((method, dict(params or {})))
        if method == "sessions.list":
            return {"sessions": [{"key": "ecom-chat-1"}]}
        return {"ok": True}


def _transport() -> tuple[OpenClawCompatTransport, _RecordingRPC]:
    rpc = _RecordingRPC()
    transport = OpenClawCompatTransport(
        GatewayConfig(url="ws://localhost:0"),
        ensure_session_fn=rpc.ensure,
        history_fn=rpc.history,
        send_fn=rpc.send,
        call_fn=rpc.call,
    )
    return transport, rpc


def test_compat_satisfies_bridge_protocol() -> None:
    transport, _ = _transport()
    assert isinstance(transport, HermesBridge)


@pytest.mark.asyncio
async def test_health_is_labeled_not_hermes() -> None:
    transport, _ = _transport()
    health = await transport.health()
    assert health.ok is True
    assert "NOT real Hermes" in (health.detail or "")


@pytest.mark.asyncio
async def test_create_session_ensures_via_sessions_patch() -> None:
    transport, rpc = _transport()
    ref = await transport.create_session(CreateSession(profile_id="x", title="T"))
    assert ref.session_id
    assert ("ensure", {"key": ref.session_id, "label": "T"}) in rpc.calls


@pytest.mark.asyncio
async def test_resume_uses_existing_session_key() -> None:
    transport, _ = _transport()
    ref = await transport.create_session(
        CreateSession(profile_id="x", resume_session_id="ecom-chat-existing")
    )
    assert ref.session_id == "ecom-chat-existing"


@pytest.mark.asyncio
async def test_get_history_parses_messages() -> None:
    transport, _ = _transport()
    history = await transport.get_history(
        HermesSessionRef(profile_id="x", session_id="s1")
    )
    assert [m.role for m in history.messages] == ["user", "assistant"]
    assert history.source == "openclaw"


@pytest.mark.asyncio
async def test_submit_prompt_sends_and_finalizes() -> None:
    transport, rpc = _transport()
    ref = HermesSessionRef(profile_id="x", session_id="s1")
    events = [e async for e in transport.submit_prompt(InteractivePrompt(ref=ref, text="q"))]
    assert events[-1].type is HermesEventType.final
    assert any(e.type is HermesEventType.message_final for e in events)
    assert ("send", {"session_key": "s1", "message": "q"}) in rpc.calls


@pytest.mark.asyncio
async def test_interrupt_maps_to_chat_abort() -> None:
    transport, rpc = _transport()
    await transport.interrupt(
        InterruptRequest(ref=HermesSessionRef(profile_id="x", session_id="s1"))
    )
    assert ("chat.abort", {"sessionKey": "s1"}) in rpc.calls


@pytest.mark.asyncio
async def test_list_sessions_maps_sessions_list() -> None:
    transport, _ = _transport()
    from app.hermes.types import SessionQuery

    page = await transport.list_sessions(SessionQuery(profile_id="x"))
    assert page.items[0].ref.session_id == "ecom-chat-1"


@pytest.mark.asyncio
async def test_background_and_branch_unsupported() -> None:
    transport, _ = _transport()
    with pytest.raises(CompatUnsupported):
        await transport.branch(
            BranchRequest(ref=HermesSessionRef(profile_id="x", session_id="s1"))
        )
    with pytest.raises(CompatUnsupported):
        await transport.start_run(
            BackgroundRunRequest(
                ecom_trace_id="t", ecom_job_id="j", workflow="w",
                hermes_profile_id="x", prompt="p",
            )
        )
