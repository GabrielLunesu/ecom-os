"""Local trace port for tool-invocation records (Runtime Spec §2.5, §7).

A02 owns the durable trace/action ledger. Until its contract lands (IR-A03-01), A03 depends
on this typed local port + ``FakeTraceSink`` so the read-tool→trace correlation slice can be
built and verified now (Operating Protocol §7). The shapes here mirror what A03 will send to
A02's ingest endpoint; they are NOT a second canonical ledger.

Coverage labels are honest (AGENTS I-12): an Ecom-OS-endpoint-handled invocation is
``verified``; a native Hermes tool call reported by a hook is ``observed``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .catalog import Coverage


@dataclass(frozen=True)
class ToolInvocationRecord:
    """The durable record A03 emits for one tool invocation (Runtime §I-05)."""

    invocation_id: str
    tool_name: str
    tool_version: str
    schema_hash: str
    coverage: Coverage
    status: str  # mirrors ToolStatus value
    trace_id: str | None
    run_id: str | None
    hermes_session_id: str | None
    hermes_tool_call_id: str | None
    arguments_redacted: dict[str, object] = field(default_factory=dict)
    error_code: str | None = None


@dataclass(frozen=True)
class NativeActivityRecord:
    """A native (non-Ecom) Hermes tool call observed via a hook — never ``verified``."""

    trace_id: str | None
    hermes_session_id: str | None
    hermes_tool_call_id: str | None
    tool_name: str
    coverage: Coverage = Coverage.observed


class TracePort(Protocol):
    async def record_tool_invocation(self, record: ToolInvocationRecord) -> None: ...
    async def record_native_activity(self, record: NativeActivityRecord) -> None: ...


class FakeTraceSink:
    """In-memory ``TracePort`` for tests/fixtures."""

    def __init__(self) -> None:
        self.invocations: list[ToolInvocationRecord] = []
        self.native: list[NativeActivityRecord] = []

    async def record_tool_invocation(self, record: ToolInvocationRecord) -> None:
        self.invocations.append(record)

    async def record_native_activity(self, record: NativeActivityRecord) -> None:
        # Defensive: a native observation must never be promoted to verified here.
        if record.coverage is Coverage.verified:
            raise ValueError("native activity cannot be recorded as verified (I-12)")
        self.native.append(record)
