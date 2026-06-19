"""Browser-facing chat gateway — the protocol safety boundary (Runtime Spec §4.1, §7 frontend).

The browser connects to an authenticated Ecom-OS endpoint, NOT to Hermes. This gateway is the
translation + allowlist layer between a browser command and the ``HermesBridge``. It enforces
the hard rules:

- The browser may invoke ONLY product-approved commands. A generic `cli.exec`, `config.set`,
  `reload.env`, `process.stop`, secret/sudo response, or any arbitrary protocol method is
  refused — there is no arbitrary protocol proxy (AGENTS §3, Runtime §4.1).
- The browser never receives a Hermes service credential or token; streamed events are
  sanitized to safe fields only (Runtime §7).
- The effective Hermes profile is resolved from the authenticated identity, never chosen by
  the browser (no profile/credential escalation, I-09).
- Reconnect queries real session status; it never infers completion from a lost socket
  (I-08, Runtime §4.1).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

from .bridge import HermesBridge
from .types import (
    BranchRequest,
    CreateSession,
    HermesEvent,
    HermesSessionRef,
    InteractivePrompt,
    InterruptRequest,
    SessionQuery,
)

# The only commands a browser client may issue. Anything else is denied — this set IS the
# product-approved surface; the upstream Hermes protocol is never proxied wholesale.
ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        "create_session",
        "resume_session",
        "list_sessions",
        "get_history",
        "get_status",
        "submit_prompt",
        "interrupt",
        "branch",
    }
)

# Keys that must never appear in a frame sent to the browser.
_FORBIDDEN_OUTPUT_KEYS: frozenset[str] = frozenset(
    {"token", "authorization", "api_key", "apikey", "secret", "credential", "password"}
)


class BrowserCommandDenied(PermissionError):
    """The browser requested a command outside the product-approved allowlist."""


@dataclass(frozen=True)
class ChatIdentity:
    """The authenticated human, resolved server-side (A01 contract; faked locally)."""

    ecom_user_id: str
    allowed_profile_id: str


class IdentityResolver(Protocol):
    async def resolve(self, token: str) -> ChatIdentity | None: ...


def _sanitize(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip any credential-like keys from an outbound payload (defense in depth)."""
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in _FORBIDDEN_OUTPUT_KEYS:
            continue
        clean[key] = value
    return clean


def safe_event(event: HermesEvent) -> dict[str, Any]:
    """Project a runtime event to the safe shape forwarded to the browser."""
    return {"type": event.type.value, "seq": event.seq, "payload": _sanitize(event.payload)}


class ChatSessionGateway:
    """Translates authenticated browser commands into allowed bridge calls."""

    def __init__(self, bridge: HermesBridge, identity: ChatIdentity) -> None:
        self._bridge = bridge
        self._identity = identity

    def _check(self, command: str) -> None:
        if command not in ALLOWED_COMMANDS:
            raise BrowserCommandDenied(
                f"command {command!r} is not a product-approved chat operation"
            )

    async def create_session(self, *, title: str | None = None) -> dict[str, Any]:
        self._check("create_session")
        # Profile comes from the authenticated identity — never browser-supplied.
        ref = await self._bridge.create_session(
            CreateSession(profile_id=self._identity.allowed_profile_id, title=title)
        )
        return {"session_id": ref.session_id, "source": ref.source}

    async def resume_session(self, *, session_id: str) -> dict[str, Any]:
        self._check("resume_session")
        ref = await self._bridge.create_session(
            CreateSession(
                profile_id=self._identity.allowed_profile_id,
                resume_session_id=session_id,
            )
        )
        return {"session_id": ref.session_id, "source": ref.source}

    async def list_sessions(self) -> dict[str, Any]:
        self._check("list_sessions")
        page = await self._bridge.list_sessions(
            SessionQuery(profile_id=self._identity.allowed_profile_id)
        )
        return {
            "sessions": [{"session_id": s.ref.session_id, "title": s.title} for s in page.items]
        }

    async def get_history(self, *, session_id: str) -> dict[str, Any]:
        self._check("get_history")
        history = await self._bridge.get_history(self._ref(session_id))
        return {
            "source": history.source,
            "messages": [{"role": m.role, "text": m.text} for m in history.messages],
        }

    async def get_status(self, *, session_id: str) -> dict[str, Any]:
        self._check("get_status")
        status = await self._bridge.get_status(self._ref(session_id))
        return {"session_id": session_id, "state": status.state.value}

    async def submit_prompt(self, *, session_id: str, text: str) -> AsyncIterator[dict[str, Any]]:
        self._check("submit_prompt")
        stream = self._bridge.submit_prompt(InteractivePrompt(ref=self._ref(session_id), text=text))
        async for event in stream:
            yield safe_event(event)

    async def interrupt(self, *, session_id: str) -> dict[str, Any]:
        self._check("interrupt")
        await self._bridge.interrupt(InterruptRequest(ref=self._ref(session_id)))
        return {"session_id": session_id, "interrupted": True}

    async def branch(self, *, session_id: str) -> dict[str, Any]:
        self._check("branch")
        ref = await self._bridge.branch(BranchRequest(ref=self._ref(session_id)))
        return {"session_id": ref.session_id}

    async def dispatch(self, command: str, params: dict[str, Any]) -> Any:
        """Generic entry point used by a WS handler; refuses anything off-allowlist."""
        self._check(command)
        handler = getattr(self, command)
        return await handler(**params)

    def _ref(self, session_id: str) -> HermesSessionRef:
        # The browser identifies a session by its Ecom-OS-safe id; the profile is bound to
        # the authenticated identity, so a client cannot address another profile's session.
        return HermesSessionRef(profile_id=self._identity.allowed_profile_id, session_id=session_id)
