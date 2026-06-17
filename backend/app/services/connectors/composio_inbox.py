"""Support-inbox connector backed by Composio (Outlook/Gmail).

Reads the per-account connection via the Composio API using `COMPOSIO_API_KEY`
(resolved as a Secret, revealed only into the request header — Invariant 5). The
brand's inbox is `info@chicagooutletshop.com` (Outlook), connected account managed
by Composio which holds and refreshes the OAuth token (Invariant 1).
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import InboxConnector
from .secrets import ConnectionRef, resolve_secret

COMPOSIO_BASE = "https://backend.composio.dev/api/v3"
API_KEY_HANDLE = "COMPOSIO_API_KEY"
MAIL_TOOLKITS = ("outlook", "gmail")
_TIMEOUT = httpx.Timeout(30.0)


class ComposioInboxConnector(InboxConnector):
    """Outlook/Gmail support inbox via Composio connected accounts."""

    def __init__(self, ref: ConnectionRef) -> None:
        super().__init__(ref)
        # ref.external_id is the Composio connected_account_id (a reference, not a secret).
        self._account_id = ref.external_id
        self._api_key = resolve_secret(API_KEY_HANDLE)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=COMPOSIO_BASE,
            headers={"x-api-key": self._api_key.reveal()},
            timeout=_TIMEOUT,
        )

    async def health(self) -> dict[str, Any]:
        """Confirm the connected mail account is ACTIVE. Returns no secrets."""
        async with self._client() as client:
            resp = await client.get(f"/connected_accounts/{self._account_id}")
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
        status = body.get("status", "UNKNOWN")
        toolkit = body.get("toolkit", {}).get("slug", "unknown")
        return {"provider": "composio", "toolkit": toolkit, "status": status}

    async def list_messages(
        self, *, unread_only: bool = True, limit: int = 25
    ) -> list[dict[str, Any]]:
        # Message ingestion is wired in build slice 7 via the Composio tool-execute API.
        raise NotImplementedError("inbox ingestion lands in build slice 7")

    async def send_message(
        self, *, to: str, subject: str, body: str, in_reply_to: str | None = None
    ) -> dict[str, Any]:
        # Outbound send is wired in build slice 10 (CS agent reply).
        raise NotImplementedError("outbound send lands in build slice 10")


async def discover_active_mail_account(api_key_handle: str = API_KEY_HANDLE) -> str | None:
    """Find an ACTIVE Outlook/Gmail connected account id, or None.

    Used by the startup health check to locate the support inbox without hardcoding
    the account id. Returns a reference (account id), never a credential.
    """
    api_key = resolve_secret(api_key_handle)
    async with httpx.AsyncClient(
        base_url=COMPOSIO_BASE,
        headers={"x-api-key": api_key.reveal()},
        timeout=_TIMEOUT,
    ) as client:
        resp = await client.get("/connected_accounts")
        resp.raise_for_status()
        items: list[dict[str, Any]] = resp.json().get("items", [])
    for acct in items:
        slug = acct.get("toolkit", {}).get("slug")
        if slug in MAIL_TOOLKITS and acct.get("status") == "ACTIVE":
            account_id: str = acct["id"]
            return account_id
    return None
