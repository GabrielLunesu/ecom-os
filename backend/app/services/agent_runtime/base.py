"""AgentRuntime — the swappable boundary for agent execution (Build Spec §6).

v1 is a thin in-app loop (`InAppCSRuntime`). An OpenClaw/Hermes or LLM-backed
runtime can drop in behind this interface without touching the dashboard. The CS
runtime is constructed with a `ShopifyConnector` (read + discounts) and an inbox
connector — never a refund tool (Invariant 2).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.tickets import Ticket


@dataclass
class HandlingResult:
    action: str  # "auto_resolved" | "escalated" | "skipped"
    new_status: str
    reply_sent: bool
    detail: str


class AgentRuntime(abc.ABC):
    @abc.abstractmethod
    async def handle_ticket(self, session: AsyncSession, ticket: Ticket) -> HandlingResult:
        """Process a single ticket and return what happened."""
