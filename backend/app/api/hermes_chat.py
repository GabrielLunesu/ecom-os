"""HTTP/SSE surface for the Hermes main chat + capability health (Build Spec Slice 3).

Exposes the already-built ``ChatSessionGateway`` (browser protocol-safety boundary) and
``hermes_health_snapshot`` as real routes. The browser talks only to these endpoints, never
to Hermes; only product-approved operations are reachable, no Hermes credential is returned,
and the effective profile is bound to the authenticated identity (Runtime §4.1, §7).

This module only *exports* ``router``. Central registration in ``app/main.py`` is performed by
the shared-file owner (A01/A09) per IR-A03-04. The bridge transport is selected from the
environment (fixture / OpenClaw-compat / real Hermes-native); against fixtures every
Hermes-dependent feature is honestly reported ``not_ready`` (I-19).

Identity→profile resolution is a placeholder pending the A01 contract (IR-A03-02): it binds
the authenticated user to a single allowed profile. The browser can never choose the profile.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api.deps import require_user_auth
from app.core.auth import AuthContext
from app.hermes.bridge import HermesBridge
from app.hermes.chat_gateway import (
    ChatIdentity,
    ChatSessionGateway,
)
from app.hermes.conformance_cli import select_transport
from app.hermes.health import hermes_health_snapshot

router = APIRouter(prefix="/hermes", tags=["hermes"])

# Placeholder default profile until A01 supplies identity→profile mapping (IR-A03-02).
_DEFAULT_PROFILE = "hp_primary"


def get_chat_bridge() -> HermesBridge:
    """Resolve the chat transport from configuration (overridable in tests)."""
    return select_transport(os.environ).bridge


def get_chat_identity(auth: AuthContext = Depends(require_user_auth)) -> ChatIdentity:
    """Bind the authenticated user to its allowed Hermes profile (browser cannot choose)."""
    user = auth.user
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return ChatIdentity(ecom_user_id=str(user.id), allowed_profile_id=_DEFAULT_PROFILE)


def get_chat_gateway(
    bridge: HermesBridge = Depends(get_chat_bridge),
    identity: ChatIdentity = Depends(get_chat_identity),
) -> ChatSessionGateway:
    return ChatSessionGateway(bridge, identity)


GATEWAY_DEP = Depends(get_chat_gateway)


class CreateSessionBody(BaseModel):
    title: str | None = None


class PromptBody(BaseModel):
    text: str


@router.get("/health")
async def get_health() -> dict[str, object]:
    """Capability + conformance snapshot for `/agents` / System health.

    Honestly reports ``conformance_blocked: true`` until a real Hermes is configured.
    """
    selected = select_transport(os.environ)
    return await hermes_health_snapshot(
        selected.bridge, is_real=selected.is_real, transport_label=selected.label
    )


@router.get("/sessions")
async def list_sessions(gw: ChatSessionGateway = GATEWAY_DEP) -> dict[str, object]:
    return await gw.list_sessions()


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionBody, gw: ChatSessionGateway = GATEWAY_DEP
) -> dict[str, object]:
    return await gw.create_session(title=body.title)


@router.post("/sessions/{session_id}/resume")
async def resume_session(
    session_id: str, gw: ChatSessionGateway = GATEWAY_DEP
) -> dict[str, object]:
    return await gw.resume_session(session_id=session_id)


@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str, gw: ChatSessionGateway = GATEWAY_DEP) -> dict[str, object]:
    return await gw.get_history(session_id=session_id)


@router.get("/sessions/{session_id}/status")
async def get_status(session_id: str, gw: ChatSessionGateway = GATEWAY_DEP) -> dict[str, object]:
    return await gw.get_status(session_id=session_id)


@router.post("/sessions/{session_id}/interrupt")
async def interrupt(session_id: str, gw: ChatSessionGateway = GATEWAY_DEP) -> dict[str, object]:
    return await gw.interrupt(session_id=session_id)


@router.post("/sessions/{session_id}/messages")
async def submit_prompt(
    session_id: str, body: PromptBody, gw: ChatSessionGateway = GATEWAY_DEP
) -> EventSourceResponse:
    """Stream safe Hermes events to the browser over SSE (no credential ever forwarded)."""

    async def _events() -> AsyncIterator[dict[str, str]]:
        async for event in gw.submit_prompt(session_id=session_id, text=body.text):
            yield {"event": "message", "data": json.dumps(event)}

    return EventSourceResponse(_events())
