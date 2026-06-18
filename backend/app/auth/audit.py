"""Audit/trace sink port for identity & config changes.

A01 must record audit events for identity/config changes (Build Spec Slice 1; data
§10 ``audit_records``) from day one, but the durable audit/trace store is owned by A02
and not yet available. This module defines the **port** A01 calls, plus a no-op default
and an in-memory test fake. When A02 ships its sink, it injects an implementation via
:func:`set_audit_sink`; A01 code never imports A02 internals (boundary rule).

Secret values must never be placed in :class:`AuditEvent.details` (AGENTS.md I-15);
record handles/ids only.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "AuditEvent",
    "AuditTraceSink",
    "NoOpAuditSink",
    "InMemoryAuditSink",
    "get_audit_sink",
    "set_audit_sink",
]


class AuditEvent(BaseModel):
    """A safe, secret-free record of a privileged identity/config change."""

    action: str = Field(description="Stable action key, e.g. 'owner.bootstrap'.")
    actor_id: str | None = Field(default=None, description="Acting principal id.")
    target: str | None = Field(default=None, description="Affected entity id/handle.")
    details: dict[str, Any] = Field(default_factory=dict, description="Safe context.")
    trace_id: str | None = None
    request_id: str | None = None


@runtime_checkable
class AuditTraceSink(Protocol):
    """Port that records :class:`AuditEvent`s durably."""

    async def record(self, event: AuditEvent) -> None:
        """Persist or forward an audit event."""
        ...


class NoOpAuditSink:
    """Default sink: structured-logs the event; persistence arrives with A02.

    This is honest about coverage (AGENTS.md I-12): until A02's durable store exists,
    audit events are observed in logs only, not durably recorded.
    """

    async def record(self, event: AuditEvent) -> None:
        """Log the audit event at INFO without persisting it."""
        logger.info(
            "audit.event.noop",
            extra={
                "audit_action": event.action,
                "actor_id": event.actor_id,
                "target": event.target,
                "trace_id": event.trace_id,
                "request_id": event.request_id,
            },
        )


class InMemoryAuditSink:
    """Test fake that retains recorded events for assertions."""

    def __init__(self) -> None:
        """Create an empty in-memory audit sink."""
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        """Append the event to the in-memory list."""
        self.events.append(event)


_sink: AuditTraceSink = NoOpAuditSink()


def get_audit_sink() -> AuditTraceSink:
    """Return the process-wide audit sink (no-op until A02 injects one)."""
    return _sink


def set_audit_sink(sink: AuditTraceSink) -> None:
    """Install the process-wide audit sink (used by A02 and tests)."""
    global _sink  # noqa: PLW0603 - single well-defined injection point
    _sink = sink
