"""HermesNativeTransport — the real pinned-Hermes boundary (Runtime Spec §4.1, §17).

This is the production transport seam against a real Hermes (NousResearch, pinned
`v0.16.0` / `v2026.6.5`, TUI Gateway JSON-RPC + API-server async runs). It is intentionally
a STUB: until a real Hermes endpoint/credentials/install target is provided, it reports an
honest "blocked" health/probe and refuses operational calls. It MUST NOT be satisfied by the
legacy OpenClaw gateway — that is a separate compatibility transport (see DR-A03-01: real
Hermes remains BLOCKED, not complete, until tested against actual Hermes).

Wiring the real protocol here later does not change any caller: domain code depends only on
the ``HermesBridge`` interface.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

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


class HermesNativeNotConfigured(RuntimeError):
    """No real Hermes endpoint is configured; the native transport is unavailable."""


class HermesNativeNotImplemented(NotImplementedError):
    """A real Hermes endpoint is configured but the native protocol is not wired yet."""


@dataclass(frozen=True)
class HermesNativeConfig:
    """Connection config for a real pinned Hermes runtime (filled when one exists)."""

    endpoint: str | None = None
    token_handle: str | None = None  # secret handle, never the raw secret
    pinned_version: str = "v2026.6.5"

    @property
    def configured(self) -> bool:
        return bool(self.endpoint)


class HermesNativeTransport:
    """Implements ``HermesBridge`` against a real Hermes — currently a blocked stub."""

    def __init__(self, config: HermesNativeConfig | None = None) -> None:
        self._config = config or HermesNativeConfig()

    @property
    def configured(self) -> bool:
        return self._config.configured

    # --- capability + health (safe to call; report honest "blocked" state) ---
    async def probe(self) -> HermesCapabilities:
        # No real endpoint → no proven capabilities → every feature stays not_ready (I-19).
        return HermesCapabilities(flags=frozenset())

    async def health(self) -> HermesHealth:
        if not self.configured:
            return HermesHealth(
                ok=False,
                detail="hermes-native transport not configured (real Hermes BLOCKED)",
            )
        return HermesHealth(
            ok=False,
            version=self._config.pinned_version,
            detail="hermes-native protocol not yet implemented",
        )

    # --- operational methods refuse until wired -----------------------------
    def _guard(self) -> None:
        if not self.configured:
            raise HermesNativeNotConfigured(
                "no real Hermes endpoint configured; use a fixture or compat transport"
            )
        raise HermesNativeNotImplemented(
            "real Hermes native transport pending implementation (DR-A03-01 blocked)"
        )

    async def create_session(self, request: CreateSession) -> HermesSessionRef:
        self._guard()
        raise AssertionError("unreachable")

    async def list_sessions(self, query: SessionQuery) -> Page:
        self._guard()
        raise AssertionError("unreachable")

    async def get_history(self, ref: HermesSessionRef) -> HermesHistory:
        self._guard()
        raise AssertionError("unreachable")

    async def get_status(self, ref: HermesSessionRef) -> HermesSessionStatus:
        self._guard()
        raise AssertionError("unreachable")

    async def submit_prompt(
        self, request: InteractivePrompt
    ) -> AsyncIterator[HermesEvent]:
        self._guard()
        raise AssertionError("unreachable")
        yield  # pragma: no cover - makes this an async generator

    async def interrupt(self, request: InterruptRequest) -> None:
        self._guard()

    async def branch(self, request: BranchRequest) -> HermesSessionRef:
        self._guard()
        raise AssertionError("unreachable")

    async def start_run(self, request: BackgroundRunRequest) -> HermesRunRef:
        self._guard()
        raise AssertionError("unreachable")

    async def stream_run(self, ref: HermesRunRef) -> AsyncIterator[HermesEvent]:
        self._guard()
        raise AssertionError("unreachable")
        yield  # pragma: no cover

    async def get_run(self, ref: HermesRunRef) -> HermesRunStatus:
        self._guard()
        raise AssertionError("unreachable")

    async def stop_run(self, ref: HermesRunRef) -> None:
        self._guard()
