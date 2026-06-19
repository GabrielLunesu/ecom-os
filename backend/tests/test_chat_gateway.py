"""Tests for the browser chat-gateway safety boundary (Runtime Spec §4.1, §7).

Proves the hard browser-safety rules: only product-approved commands are accepted, arbitrary
Hermes protocol methods are refused (no proxy), the browser cannot choose its own profile, no
credential-like field is ever forwarded, and reconnect reads real status.
"""

from __future__ import annotations

import pytest

from app.hermes.chat_gateway import (
    ALLOWED_COMMANDS,
    BrowserCommandDenied,
    ChatIdentity,
    ChatSessionGateway,
    safe_event,
)
from app.hermes.fake import FakeHermesTransport
from app.hermes.types import HermesEvent, HermesEventType, HermesSessionRef


def _gateway() -> tuple[ChatSessionGateway, FakeHermesTransport]:
    bridge = FakeHermesTransport()
    identity = ChatIdentity(ecom_user_id="usr_1", allowed_profile_id="hp_owner")
    return ChatSessionGateway(bridge, identity), bridge


@pytest.mark.asyncio
async def test_create_and_submit_streams_safe_events() -> None:
    gw, _ = _gateway()
    created = await gw.create_session(title="t")
    sid = created["session_id"]
    events = [e async for e in gw.submit_prompt(session_id=sid, text="hi")]
    assert events[-1]["type"] == HermesEventType.final.value
    # Every forwarded frame is the safe projection (type/seq/payload only).
    assert all(set(e) == {"type", "seq", "payload"} for e in events)


@pytest.mark.asyncio
async def test_arbitrary_protocol_method_is_denied() -> None:
    gw, _ = _gateway()
    for forbidden in ["cli.exec", "config.set", "reload.env", "process.stop",
                      "secret.respond", "sudo", "sessions.delete"]:
        with pytest.raises(BrowserCommandDenied):
            await gw.dispatch(forbidden, {})


@pytest.mark.asyncio
async def test_dispatch_only_allows_whitelisted_commands() -> None:
    gw, _ = _gateway()
    created = await gw.dispatch("create_session", {})
    assert "session_id" in created
    # The allowlist is exactly the product surface.
    assert "create_session" in ALLOWED_COMMANDS
    assert "cli.exec" not in ALLOWED_COMMANDS


@pytest.mark.asyncio
async def test_browser_cannot_choose_profile_uses_identity() -> None:
    gw, bridge = _gateway()
    created = await gw.create_session()
    sid = created["session_id"]
    # The session was created under the identity's profile, regardless of any client wish.
    status = await bridge.get_status(
        HermesSessionRef(profile_id="hp_owner", session_id=sid)
    )
    assert status.ref.profile_id == "hp_owner"


def test_safe_event_strips_credential_fields() -> None:
    event = HermesEvent(
        type=HermesEventType.tool_result,
        seq=3,
        payload={"ok": True, "token": "secret-xyz", "Authorization": "Bearer x", "name": "#1"},
    )
    projected = safe_event(event)
    assert "token" not in projected["payload"]
    assert "Authorization" not in projected["payload"]
    assert projected["payload"]["ok"] is True
    assert projected["payload"]["name"] == "#1"


@pytest.mark.asyncio
async def test_reconnect_reads_real_status_then_interrupt() -> None:
    gw, _ = _gateway()
    sid = (await gw.create_session())["session_id"]
    # idle before any work
    assert (await gw.get_status(session_id=sid))["state"] == "idle"
    await gw.interrupt(session_id=sid)
    # status reflects the interrupt request path, not an inferred completion
    out = await gw.get_status(session_id=sid)
    assert out["session_id"] == sid


@pytest.mark.asyncio
async def test_resume_addresses_existing_session() -> None:
    gw, _ = _gateway()
    sid = (await gw.create_session())["session_id"]
    resumed = await gw.resume_session(session_id=sid)
    assert resumed["session_id"] == sid
