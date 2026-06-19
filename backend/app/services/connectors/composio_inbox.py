"""Support-inbox connector backed by Composio (Outlook/Gmail).

Reads the per-account connection via the Composio API using `COMPOSIO_API_KEY`
(resolved as a Secret, revealed only into the request header — Invariant 5). The
brand's inbox is `info@chicagooutletshop.com` (Outlook); Composio holds and refreshes
the OAuth token (Invariant 1).
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

import httpx

from .base import InboxConnector
from .secrets import ConnectionRef, resolve_secret

_URL_RE = re.compile(r"(https?://[^\s<>]+)")


def text_to_html(text: str) -> str:
    """Render a plain-text message body as simple, safe HTML email.

    Blank lines become paragraphs, single newlines become <br>, and URLs become
    clickable links. Fixes the "wall of text" plain-text replies in Outlook.
    """
    paragraphs = re.split(r"\n\s*\n", (text or "").strip())
    blocks: list[str] = []
    for para in paragraphs:
        escaped = _html.escape(para)
        linked = _URL_RE.sub(r'<a href="\1">\1</a>', escaped)
        blocks.append("<p>" + linked.replace("\n", "<br>") + "</p>")
    inner = "".join(blocks)
    return (
        '<div style="font-family:Inter,Segoe UI,Arial,sans-serif;font-size:14px;'
        'line-height:1.6;color:#0b1220">' + inner + "</div>"
    )


COMPOSIO_BASE = "https://backend.composio.dev/api/v3"
API_KEY_HANDLE = "COMPOSIO_API_KEY"
MAIL_TOOLKITS = ("outlook", "gmail")
_TIMEOUT = httpx.Timeout(40.0)

# Outlook tool slugs (Gmail equivalents swap in behind this connector later).
TOOL_LIST = "OUTLOOK_OUTLOOK_LIST_MESSAGES"
TOOL_REPLY = "OUTLOOK_OUTLOOK_REPLY_EMAIL"
TOOL_SEND = "OUTLOOK_OUTLOOK_SEND_EMAIL"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    text = _TAG_RE.sub(" ", html or "")
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return _WS_RE.sub(" ", text).strip()


def normalize_message(m: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Microsoft Graph message into our ticket-ingestion shape."""
    frm = (
        ((m.get("from") or {}).get("emailAddress") or {}) if isinstance(m.get("from"), dict) else {}
    )
    body = m.get("body") or {}
    content = body.get("content", "")
    text = _html_to_text(content) if body.get("contentType") == "html" else (content or "")
    return {
        "external_id": m.get("id", ""),
        "conversation_id": m.get("conversationId", ""),
        "subject": m.get("subject", "") or "(no subject)",
        "from_email": frm.get("address", ""),
        "from_name": frm.get("name", ""),
        "body_text": text,
        "received_at": m.get("receivedDateTime", ""),
        "is_read": bool(m.get("isRead", False)),
    }


class ComposioInboxConnector(InboxConnector):
    """Outlook/Gmail support inbox via Composio connected accounts."""

    def __init__(self, ref: ConnectionRef) -> None:
        super().__init__(ref)
        # ref.external_id is the Composio connected_account_id (a reference, not a secret).
        self._account_id = ref.external_id
        self._api_key = resolve_secret(API_KEY_HANDLE)
        self._user_id: str | None = None

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=COMPOSIO_BASE,
            headers={"x-api-key": self._api_key.reveal()},
            timeout=_TIMEOUT,
        )

    async def _account(self) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.get(f"/connected_accounts/{self._account_id}")
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
            return body

    async def _ensure_user_id(self) -> str:
        if self._user_id is None:
            acct = await self._account()
            self._user_id = str(acct.get("user_id", ""))
        return self._user_id

    async def _execute(self, tool_slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        user_id = await self._ensure_user_id()
        async with self._client() as client:
            resp = await client.post(
                f"/tools/execute/{tool_slug}",
                json={
                    "connected_account_id": self._account_id,
                    "user_id": user_id,
                    "arguments": arguments,
                },
            )
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
        if not body.get("successful", body.get("success")):
            raise RuntimeError(f"composio tool {tool_slug} failed: {body.get('error')}")
        data: dict[str, Any] = body.get("data", {})
        return data

    async def health(self) -> dict[str, Any]:
        """Confirm the connected mail account is ACTIVE. Returns no secrets."""
        acct = await self._account()
        return {
            "provider": "composio",
            "toolkit": (acct.get("toolkit") or {}).get("slug", "unknown"),
            "status": acct.get("status", "UNKNOWN"),
        }

    async def list_messages(
        self, *, unread_only: bool = True, limit: int = 25
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {"top": min(limit, 50)}
        if unread_only:
            args["is_read"] = False
        data = await self._execute(TOOL_LIST, args)
        value = (data.get("response_data") or {}).get("value", [])
        return [normalize_message(m) for m in value if isinstance(m, dict)]

    async def send_message(
        self, *, to: str, subject: str, body: str, in_reply_to: str | None = None
    ) -> dict[str, Any]:
        """Send a formatted (HTML) reply email.

        Plain-text replies collapse line breaks in Outlook, so we always send HTML
        (paragraphs, <br>, clickable links). HTML can't ride the plain-text reply
        comment, so we send a "Re:" email; ticket threading is matched on the inbound
        side by conversation id + customer email (see services/tickets.py).
        """
        re_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        return await self._execute(
            TOOL_SEND,
            {"to_email": to, "subject": re_subject, "body": text_to_html(body), "is_html": True},
        )


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
