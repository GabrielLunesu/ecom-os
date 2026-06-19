"""Agent templates + config (Build Spec §7.5). Templates are fixed; operators
configure voice, SOPs, allowed tools, and schedule — never open-ended creation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.agent_config import AgentConfig
from app.models.brand import Brand

# Fixed templates. The CS template's tools are read + discounts only — there is no
# refund tool to grant (Invariant 2): capability is bound by the connector layer.
TEMPLATES: list[dict[str, Any]] = [
    {
        "template": "cs",
        "name": "Customer Service",
        "description": "Handles WISMO and support tickets; escalates to a rep.",
        "default_tools": ["read_orders", "read_fulfillments", "read_customers", "write_discounts"],
    },
    {
        "template": "analytics",
        "name": "Analytics",
        "description": "Summarizes KPIs and surfaces anomalies.",
        "default_tools": ["read_orders", "read_reports"],
    },
    {
        "template": "content",
        "name": "Content",
        "description": "Drafts product and marketing copy from the brand vault.",
        "default_tools": ["read_products", "read_content"],
    },
    {
        "template": "retention",
        "name": "Retention",
        "description": "Win-back and loyalty flows with capped discounts.",
        "default_tools": ["read_customers", "write_discounts"],
    },
]


def list_templates() -> list[dict[str, Any]]:
    return TEMPLATES


async def ensure_seed_agents(session: AsyncSession, brand: Brand) -> None:
    existing = (await session.exec(select(AgentConfig).where(AgentConfig.template == "cs"))).first()
    if existing is None:
        session.add(
            AgentConfig(
                brand_id=brand.id,
                template="cs",
                name="Chicago Outlet CS",
                voice="Friendly, concise, on-brand. Always cite policy and the tracking page.",
                sops="WISMO: look up the order, cite the shipping policy, redirect to the "
                "tracking page, then auto-close. Anything else -> escalate to a rep.",
                allowed_tools=[
                    "read_orders",
                    "read_fulfillments",
                    "read_customers",
                    "write_discounts",
                ],
                schedule="webhook",
                enabled=True,
            )
        )
        await session.commit()


async def list_agents(session: AsyncSession) -> list[AgentConfig]:
    return list((await session.exec(select(AgentConfig).order_by(AgentConfig.name))).all())


async def update_agent(
    session: AsyncSession, agent_id: UUID, *, voice: str, sops: str, schedule: str, enabled: bool
) -> AgentConfig | None:
    agent = (await session.exec(select(AgentConfig).where(AgentConfig.id == agent_id))).first()
    if agent is None:
        return None
    agent.voice = voice
    agent.sops = sops
    agent.schedule = schedule
    agent.enabled = enabled
    agent.updated_at = utcnow()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent
