"""HermesRuntime: the production CS brain, routed through a Hermes subagent.

Same `AgentRuntime` contract as `LLMCSRuntime`; the only thing that changes is *where
the reasoning/tool step runs*. When `HERMES_GATEWAY_URL` is set, the LLM step is
delegated to a Hermes `cs` subagent through Hermes's Tool Gateway:

    Hermes `delegate` ──▶ subagent (profile=cs)
        profile `cs` grants read + write_discounts tools ONLY — literally no refund
        tool exists in the profile (Invariant 2, enforced by Hermes scoping).
        The subagent runs the same tool-use loop and decision logic; the backend
        stays the system of record (tickets, evidence, audit, vault, approval lane).

Because Hermes is not installed in this environment, the delegated path is wired as a
thin override of `LLMCSRuntime._create_message`: it POSTs the same Messages-API-shaped
request to the Hermes gateway's `delegate` endpoint with a scoped `cs` profile instead
of calling Anthropic directly. The gateway is responsible for tool scoping, model
selection, and credential handling on its side. When `HERMES_GATEWAY_URL` is unset we
fall back to the direct Anthropic path inherited from `LLMCSRuntime`, so the runtime is
always functional. Every Invariant (2 no-refund, 3 sticky, 4 untrusted-delimited,
5 no-secret-leak) is inherited unchanged from `LLMCSRuntime`.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.connectors.base import InboxConnector, ShopifyConnector
from app.services.connectors.secrets import Secret, env_or_setting, resolve_secret

from .llm import _MAX_TOKENS, _TIMEOUT, SYSTEM_PROMPT, TOOLS, LLMCSRuntime

logger = get_logger(__name__)

_GATEWAY_HANDLE = "HERMES_GATEWAY_URL"
_GATEWAY_TOKEN_HANDLE = "HERMES_API_KEY"
# The scoped Hermes profile that exposes read + discount tools and no refund tool.
_CS_PROFILE = "cs"


class HermesRuntime(LLMCSRuntime):
    """LLM CS runtime whose reasoning step is delegated to a Hermes `cs` subagent."""

    def __init__(
        self,
        shopify: ShopifyConnector,
        inbox: InboxConnector,
        store_domain: str,
        *,
        model: str = "claude-opus-4-8",
        api_base: str = "https://api.anthropic.com",
    ) -> None:
        super().__init__(shopify, inbox, store_domain, model=model, api_base=api_base)
        # Non-secret gateway URL; empty -> fall back to the direct Anthropic path.
        self.gateway_url = env_or_setting(_GATEWAY_HANDLE).rstrip("/")

    async def _create_message(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.gateway_url:
            # Hermes not configured: use the inherited direct Anthropic path.
            return await super()._create_message(messages)

        # Resolve the gateway token if present; never logged (Invariant 5).
        token: Secret | None = None
        try:
            token = resolve_secret(_GATEWAY_TOKEN_HANDLE)
        except Exception:  # noqa: BLE001 - gateway may be unauthenticated locally
            token = None
        headers = {"content-type": "application/json"}
        if token is not None:
            headers["authorization"] = f"Bearer {token.reveal()}"

        payload = {
            "profile": _CS_PROFILE,  # scoped: read + discounts, NO refund tool (Invariant 2).
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "tools": TOOLS,
            "messages": messages,
        }
        async with httpx.AsyncClient(base_url=self.gateway_url, timeout=_TIMEOUT) as client:
            resp = await client.post("/delegate", headers=headers, json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data
