"""The HermesBridge protocol (Runtime Spec §2.2).

Domain code depends on this interface, never on a concrete transport. Two supported
transports back it: interactive (TUI Gateway JSON-RPC) and background (API-server async
runs). ``FakeHermesTransport`` implements it for conformance fixtures.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .types import (
    BackgroundRunRequest,
    BranchRequest,
    CreateSession,
    HermesCapabilities,
    HermesEvent,
    HermesHealth,
    HermesHistory,
    HermesRunRef,
    HermesRunStatus,
    HermesSessionRef,
    HermesSessionStatus,
    InteractivePrompt,
    InterruptRequest,
    Page,
    SessionQuery,
)


@runtime_checkable
class HermesBridge(Protocol):
    # capability + health
    async def probe(self) -> HermesCapabilities: ...
    async def health(self) -> HermesHealth: ...

    # interactive sessions
    async def create_session(self, request: CreateSession) -> HermesSessionRef: ...
    async def list_sessions(self, query: SessionQuery) -> Page: ...
    async def get_history(self, ref: HermesSessionRef) -> HermesHistory: ...
    async def get_status(self, ref: HermesSessionRef) -> HermesSessionStatus: ...
    def submit_prompt(self, request: InteractivePrompt) -> AsyncIterator[HermesEvent]: ...
    async def interrupt(self, request: InterruptRequest) -> None: ...
    async def branch(self, request: BranchRequest) -> HermesSessionRef: ...

    # background runs
    async def start_run(self, request: BackgroundRunRequest) -> HermesRunRef: ...
    def stream_run(self, ref: HermesRunRef) -> AsyncIterator[HermesEvent]: ...
    async def get_run(self, ref: HermesRunRef) -> HermesRunStatus: ...
    async def stop_run(self, ref: HermesRunRef) -> None: ...
