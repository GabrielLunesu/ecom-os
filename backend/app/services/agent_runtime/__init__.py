"""Agent runtimes behind one swappable interface (Build Spec §6).

- InAppCSRuntime  — deterministic WISMO SOP (no LLM; default).
- LLMCSRuntime    — Anthropic tool-use loop (read + discounts, never refunds).
- HermesRuntime   — routes the LLM step through a Hermes `cs` subagent; falls back
  to the direct Anthropic path when HERMES_GATEWAY_URL is unset.

All three implement the same `AgentRuntime` contract and are constructed with a
read+discount ShopifyConnector and the inbox connector — never a refund tool (Inv 2).
"""

from __future__ import annotations

from .base import AgentRuntime, HandlingResult
from .flow import FlowCSRuntime
from .hermes import HermesRuntime
from .in_app import InAppCSRuntime
from .llm import LLMCSRuntime

__all__ = [
    "AgentRuntime",
    "HandlingResult",
    "InAppCSRuntime",
    "FlowCSRuntime",
    "LLMCSRuntime",
    "HermesRuntime",
]
