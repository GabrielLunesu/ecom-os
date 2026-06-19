"""In-memory HermesBridge for conformance fixtures (Operating Protocol §7).

This is NOT a Hermes emulator and NOT a production transport. It exercises the bridge
contract — ordered streaming, resume/history, interrupt, branch, background runs — so the
Slice 0 spikes and conformance suite run before a real Hermes release is pinned. Probes
against it are marked ``is_real=False`` so no feature is wrongly promoted to ``ready``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TypedDict

from .capabilities import REQUIRED_FLAGS
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
    HermesSessionSummary,
    InteractivePrompt,
    InterruptRequest,
    Page,
    RunState,
    SessionQuery,
    SessionState,
)

# Streamed interactive steps the fake replays for any prompt (deterministic, ordered).
_INTERACTIVE_STEPS: tuple[tuple[HermesEventType, dict[str, object]], ...] = (
    (HermesEventType.message_delta, {"text": "Looking into it."}),
    (HermesEventType.tool_start, {"tool": "ecom.order.get"}),
    (HermesEventType.tool_result, {"tool": "ecom.order.get", "ok": True}),
    (HermesEventType.message_delta, {"text": " Done."}),
    (HermesEventType.message_final, {"text": "Looking into it. Done."}),
)
_ASSISTANT_REPLY = "Looking into it. Done."


class _SessionRecord(TypedDict):
    profile_id: str
    title: str | None
    history: list[HermesMessage]
    state: SessionState
    last_seen: str | None


class _RunRecord(TypedDict):
    profile_id: str
    state: RunState
    trace_id: str


class FakeHermesTransport:
    """A minimal in-memory implementation of the ``HermesBridge`` protocol."""

    def __init__(
        self,
        *,
        flags: frozenset[str] | None = None,
        version: str = "fake-0.0.0",
        profile_fingerprint: str = "fp_fake",
    ) -> None:
        self._flags = frozenset(REQUIRED_FLAGS) if flags is None else flags
        self._version = version
        self._profile_fingerprint = profile_fingerprint
        self._sessions: dict[str, _SessionRecord] = {}
        self._interrupted: dict[str, bool] = {}
        self._runs: dict[str, _RunRecord] = {}
        self._seq = 0

    # --- capability + health ---
    async def probe(self) -> HermesCapabilities:
        return HermesCapabilities(flags=self._flags)

    async def health(self) -> HermesHealth:
        return HermesHealth(ok=True, version=self._version, profile_id="hp_fake")

    @property
    def profile_fingerprint(self) -> str:
        return self._profile_fingerprint

    # --- interactive sessions ---
    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    def _require(self, ref: HermesSessionRef) -> _SessionRecord:
        session = self._sessions.get(ref.session_id)
        if session is None:
            raise KeyError(f"unknown session: {ref.session_id}")
        return session

    async def create_session(self, request: CreateSession) -> HermesSessionRef:
        if request.resume_session_id is not None:
            # Resume is addressing an existing canonical session, not a copy.
            existing = self._sessions.get(request.resume_session_id)
            if existing is None:
                raise KeyError(f"cannot resume unknown session: {request.resume_session_id}")
            return HermesSessionRef(
                profile_id=request.profile_id,
                session_id=request.resume_session_id,
                source=request.source,
            )
        session_id = self._next_id("hs")
        self._sessions[session_id] = {
            "profile_id": request.profile_id,
            "title": request.title,
            "history": [],
            "state": SessionState.idle,
            "last_seen": "t0",
        }
        return HermesSessionRef(
            profile_id=request.profile_id, session_id=session_id, source=request.source
        )

    async def list_sessions(self, query: SessionQuery) -> Page:
        items = tuple(
            HermesSessionSummary(
                ref=HermesSessionRef(profile_id=query.profile_id, session_id=sid),
                title=data["title"],
                last_seen=data["last_seen"],
            )
            for sid, data in self._sessions.items()
            if data["profile_id"] == query.profile_id
        )
        return Page(items=items[: query.limit])

    async def get_history(self, ref: HermesSessionRef) -> HermesHistory:
        session = self._require(ref)
        return HermesHistory(ref=ref, messages=tuple(session["history"]))

    async def get_status(self, ref: HermesSessionRef) -> HermesSessionStatus:
        session = self._require(ref)
        return HermesSessionStatus(ref=ref, state=session["state"])

    async def submit_prompt(self, request: InteractivePrompt) -> AsyncIterator[HermesEvent]:
        session = self._require(request.ref)
        sid = request.ref.session_id
        history = session["history"]
        history.append(HermesMessage(role="user", text=request.text))
        session["state"] = SessionState.running
        seq = 0
        for event_type, payload in _INTERACTIVE_STEPS:
            # Honor an interrupt requested between event boundaries; never infer
            # completion when the user cancelled (AGENTS I-08).
            if self._interrupted.pop(sid, False):
                session["state"] = SessionState.interrupted
                yield HermesEvent(type=HermesEventType.interrupted, seq=seq, payload={})
                return
            yield HermesEvent(type=event_type, seq=seq, payload=dict(payload))
            seq += 1
        history.append(HermesMessage(role="assistant", text=_ASSISTANT_REPLY))
        session["state"] = SessionState.idle
        yield HermesEvent(type=HermesEventType.final, seq=seq, payload={})

    async def interrupt(self, request: InterruptRequest) -> None:
        self._require(request.ref)
        self._interrupted[request.ref.session_id] = True

    async def branch(self, request: BranchRequest) -> HermesSessionRef:
        source = self._require(request.ref)
        new_id = self._next_id("hs")
        self._sessions[new_id] = {
            "profile_id": source["profile_id"],
            "title": f"branch of {request.ref.session_id}",
            "history": list(source["history"]),
            "state": SessionState.idle,
            "last_seen": "t0",
        }
        return HermesSessionRef(
            profile_id=request.ref.profile_id, session_id=new_id, source=request.ref.source
        )

    # --- background runs ---
    async def start_run(self, request: BackgroundRunRequest) -> HermesRunRef:
        run_id = self._next_id("hr")
        self._runs[run_id] = {
            "profile_id": request.hermes_profile_id,
            "state": RunState.running,
            "trace_id": request.ecom_trace_id,
        }
        return HermesRunRef(profile_id=request.hermes_profile_id, run_id=run_id)

    async def stream_run(self, ref: HermesRunRef) -> AsyncIterator[HermesEvent]:
        if ref.run_id not in self._runs:
            raise KeyError(f"unknown run: {ref.run_id}")
        seq = 0
        for event_type, payload in _INTERACTIVE_STEPS:
            yield HermesEvent(type=event_type, seq=seq, payload=dict(payload))
            seq += 1
        self._runs[ref.run_id]["state"] = RunState.completed
        yield HermesEvent(type=HermesEventType.final, seq=seq, payload={})

    async def get_run(self, ref: HermesRunRef) -> HermesRunStatus:
        run = self._runs.get(ref.run_id)
        if run is None:
            return HermesRunStatus(ref=ref, state=RunState.unknown)
        return HermesRunStatus(ref=ref, state=run["state"])

    async def stop_run(self, ref: HermesRunRef) -> None:
        run = self._runs.get(ref.run_id)
        if run is not None:
            run["state"] = RunState.stopped

    def force_complete_run(self, ref: HermesRunRef) -> None:
        """Test helper: mark a run completed as if it finished after a dropped stream."""
        if ref.run_id in self._runs:
            self._runs[ref.run_id]["state"] = RunState.completed
