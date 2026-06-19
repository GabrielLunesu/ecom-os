"""Health and readiness probe response schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field
from sqlmodel import SQLModel


class ComponentHealthModel(SQLModel):
    """One health dimension's state and detail."""

    name: str = Field(description="Dimension name, e.g. 'database'.")
    state: str = Field(description="One of: ok, degraded, down, unknown.")
    detail: str | None = Field(default=None, description="Human-readable context.")


class HealthReportResponse(SQLModel):
    """Multi-dimension readiness report (a single green/red light is insufficient)."""

    state: str = Field(description="Overall state derived from owned dimensions.")
    ready: bool = Field(description="Whether the service is ready to serve reads.")
    components: list[ComponentHealthModel] = Field(default_factory=list)


class HealthStatusResponse(SQLModel):
    """Standard payload for service liveness/readiness checks."""

    ok: bool = Field(
        description="Indicates whether the probe check succeeded.",
        examples=[True],
    )


class AgentHealthStatusResponse(HealthStatusResponse):
    """Agent-authenticated liveness payload for agent route probes."""

    agent_id: UUID = Field(
        description="Authenticated agent id derived from `X-Agent-Token`.",
        examples=["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    )
    board_id: UUID | None = Field(
        default=None,
        description="Board scope for the authenticated agent, when applicable.",
        examples=["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"],
    )
    gateway_id: UUID = Field(
        description="Gateway owning the authenticated agent.",
        examples=["cccccccc-cccc-cccc-cccc-cccccccccccc"],
    )
    status: str = Field(
        description="Current persisted lifecycle status for the authenticated agent.",
        examples=["online", "healthy", "updating"],
    )
    is_board_lead: bool = Field(
        description="Whether the authenticated agent is the board lead.",
        examples=[False],
    )
