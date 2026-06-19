"""Health-check primitives.

Normative basis: `05-OPERATIONS-AND-SECURITY.md` §11.1 — the System page and ``/health``
APIs must distinguish liveness, readiness to serve authenticated reads, connector
health, queue/lease health, reconciliation backlog, trace ingest lag, backup freshness,
and Hermes/adapter compatibility. "A single green/red light is insufficient."

A01 owns the *primitives* and the readiness dimensions it can truthfully assess now
(process liveness, database connectivity, migration state). Dimensions owned by other
domains (connectors=A04, queue/traces=A02, backup/extensions=A09, Hermes=A03) appear in
the report as ``unknown`` placeholders — honest coverage (AGENTS.md I-12), to be wired
by their owners through this same structure.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)

__all__ = [
    "HealthState",
    "ComponentHealth",
    "check_database",
    "check_migrations",
    "build_readiness_report",
]


class HealthState(str, Enum):
    """Health state for a component or the overall report."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class ComponentHealth:
    """A single health dimension's state and human-readable detail."""

    __slots__ = ("name", "state", "detail")

    def __init__(self, name: str, state: HealthState, detail: str | None = None) -> None:
        """Record a component's name, state, and optional detail."""
        self.name = name
        self.state = state
        self.detail = detail

    def as_dict(self) -> dict[str, str | None]:
        """Return a JSON-safe representation."""
        return {"name": self.name, "state": self.state.value, "detail": self.detail}


# Dimensions A01 does not own; surfaced as unknown until their owner wires a real check.
_DEFERRED_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("connectors", "owned by A04; not wired"),
    ("queue_and_leases", "owned by A02; not wired"),
    ("action_reconciliation", "owned by A02; not wired"),
    ("trace_ingest", "owned by A02; not wired"),
    ("backup_freshness", "owned by A09; not wired"),
    ("hermes_compatibility", "owned by A03; not wired"),
    ("extensions", "owned by A09; not wired"),
)


async def check_database(session: AsyncSession) -> ComponentHealth:
    """Verify the database answers a trivial query (readiness to serve reads)."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure means not-ready
        logger.warning("health.database.down", extra={"error": str(exc)[:200]})
        return ComponentHealth("database", HealthState.DOWN, "query failed")
    return ComponentHealth("database", HealthState.OK)


async def check_migrations(session: AsyncSession) -> ComponentHealth:
    """Report whether the DB's Alembic revision matches the code's head revision."""
    try:
        from alembic.script import ScriptDirectory

        from app.db.session import _alembic_config

        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar_one_or_none()
        head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    except Exception as exc:  # noqa: BLE001 - best-effort, never fatal
        return ComponentHealth("migrations", HealthState.UNKNOWN, f"unreadable: {str(exc)[:120]}")
    if current is None:
        return ComponentHealth("migrations", HealthState.UNKNOWN, "no alembic_version row")
    if current != head:
        return ComponentHealth(
            "migrations",
            HealthState.DEGRADED,
            f"db at {current}, head {head}",
        )
    return ComponentHealth("migrations", HealthState.OK, current)


async def build_readiness_report(
    session: AsyncSession,
) -> tuple[HealthState, list[ComponentHealth]]:
    """Assemble the readiness report; overall state derives from owned dimensions."""
    components = [
        ComponentHealth("liveness", HealthState.OK),
        await check_database(session),
        await check_migrations(session),
    ]
    # Readiness to serve authenticated reads turns on liveness + database.
    overall = HealthState.OK
    if any(c.state is HealthState.DOWN for c in components):
        overall = HealthState.DOWN
    elif any(c.state is HealthState.DEGRADED for c in components):
        overall = HealthState.DEGRADED

    components.extend(
        ComponentHealth(name, HealthState.UNKNOWN, detail)
        for name, detail in _DEFERRED_DIMENSIONS
    )
    return overall, components
