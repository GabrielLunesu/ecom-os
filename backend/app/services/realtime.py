"""Realtime email triggers via Composio (OUTLOOK_MESSAGE_TRIGGER).

Enabling the trigger makes Composio watch the inbox and POST our webhook the moment a
new email arrives — turning the ~2 min cron poll into near-instant handling. The cron
stays as a fallback.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.connectors.composio_inbox import COMPOSIO_BASE, discover_active_mail_account
from app.services.connectors.secrets import resolve_secret

logger = get_logger(__name__)
TRIGGER_SLUG = "OUTLOOK_MESSAGE_TRIGGER"
_TIMEOUT = httpx.Timeout(30.0)


def _client() -> httpx.AsyncClient:
    api_key = resolve_secret("COMPOSIO_API_KEY")
    return httpx.AsyncClient(
        base_url=COMPOSIO_BASE, headers={"x-api-key": api_key.reveal()}, timeout=_TIMEOUT
    )


async def enable_email_trigger() -> dict[str, Any]:
    """Create/refresh the new-email trigger for the connected inbox."""
    account_id = await discover_active_mail_account()
    if not account_id:
        return {"enabled": False, "detail": "no inbox connected"}
    async with _client() as client:
        resp = await client.post(
            f"/trigger_instances/{TRIGGER_SLUG}/upsert",
            json={"connected_account_id": account_id},
        )
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()
    return {"enabled": True, "trigger_id": body.get("trigger_id"), "account": account_id}


async def realtime_status() -> dict[str, Any]:
    """Report whether the new-email trigger is active."""
    try:
        async with _client() as client:
            resp = await client.get("/trigger_instances/active", params={"limit": 50})
            resp.raise_for_status()
            items = resp.json().get("items", [])
    except Exception:  # noqa: BLE001 - status must never crash the page
        return {"enabled": False, "detail": "could not reach Composio"}
    active = any(TRIGGER_SLUG in json.dumps(i) for i in items)
    return {"enabled": active}
