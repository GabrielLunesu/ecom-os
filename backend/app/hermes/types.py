"""Typed references and runtime events crossing the HermesBridge (Runtime Spec §2.2/§4).

Hermes session/run IDs are canonical; Ecom-OS stores references and derived metadata, never
a competing transcript (AGENTS I-02). All transport details stay behind these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class HermesCapabilities:
    """The set of capability flags a probed Hermes runtime reports (Runtime §3.2)."""

    flags: frozenset[str] = field(default_factory=frozenset)

    def has(self, flag: str) -> bool:
        return flag in self.flags


@dataclass(frozen=True)
class HermesHealth:
    ok: bool
    version: str | None = None
    profile_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class HermesSessionRef:
    """A reference to a canonical Hermes session (Runtime §4.3)."""

    profile_id: str
    session_id: str
    source: str = "dashboard"


@dataclass(frozen=True)
class CreateSession:
    profile_id: str
    source: str = "dashboard"
    title: str | None = None
    # When set, resume an existing canonical session instead of creating a new one.
    resume_session_id: str | None = None


@dataclass(frozen=True)
class HermesSessionSummary:
    ref: HermesSessionRef
    title: str | None
    last_seen: str | None


@dataclass(frozen=True)
class SessionQuery:
    profile_id: str
    limit: int = 50


@dataclass(frozen=True)
class Page:
    items: tuple[HermesSessionSummary, ...]
    next_cursor: str | None = None


@dataclass(frozen=True)
class HermesMessage:
    role: str  # "user" | "assistant" | "tool"
    text: str


@dataclass(frozen=True)
class HermesHistory:
    """Visible history retrieved from Hermes; not a canonical Ecom-OS store."""

    ref: HermesSessionRef
    messages: tuple[HermesMessage, ...]
    source: str = "hermes"  # provenance label for any UI cache (Runtime §4.3)


class SessionState(str, Enum):
    idle = "idle"
    running = "running"
    interrupted = "interrupted"
    unknown = "unknown"


@dataclass(frozen=True)
class HermesSessionStatus:
    ref: HermesSessionRef
    state: SessionState
    usage: dict[str, int] | None = None


@dataclass(frozen=True)
class InteractivePrompt:
    ref: HermesSessionRef
    text: str


@dataclass(frozen=True)
class InterruptRequest:
    ref: HermesSessionRef


@dataclass(frozen=True)
class BranchRequest:
    ref: HermesSessionRef


class HermesEventType(str, Enum):
    message_delta = "message_delta"
    message_final = "message_final"
    tool_start = "tool_start"
    tool_result = "tool_result"
    clarification = "clarification"
    approval = "approval"
    final = "final"
    interrupted = "interrupted"
    error = "error"


@dataclass(frozen=True)
class HermesEvent:
    """One ordered runtime event. ``seq`` is monotonic within a stream."""

    type: HermesEventType
    seq: int
    payload: dict[str, object] = field(default_factory=dict)


# --- background runs (Runtime §5) --------------------------------------------
@dataclass(frozen=True)
class BackgroundRunRequest:
    ecom_trace_id: str
    ecom_job_id: str
    workflow: str
    hermes_profile_id: str
    prompt: str
    session_strategy: str = "new"  # new | resume_entity | resume_explicit
    hermes_session_ref: HermesSessionRef | None = None
    requested_tools: tuple[str, ...] = ()
    deadline_at: str | None = None


@dataclass(frozen=True)
class HermesRunRef:
    profile_id: str
    run_id: str
    session_id: str | None = None


class RunState(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    stopped = "stopped"
    failed = "failed"
    unknown = "unknown"


@dataclass(frozen=True)
class HermesRunStatus:
    ref: HermesRunRef
    state: RunState
    detail: str | None = None
