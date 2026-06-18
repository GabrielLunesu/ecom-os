"""Inbox adapter (Composio) bound to one EXACT connected account.

Unlike the prototype's ``discover_active_mail_account`` (first ACTIVE account wins),
this adapter never selects an account: it uses ``binding.account_ref`` as the pinned
Composio ``connected_account_id`` (I-09). Account discovery is a one-time, explicit
operator action that produces a stored connection — not a per-call selection.

The adapter normalizes inbound mail into message records; the *event* emission for
A05 lives in :mod:`app.connectors.events`. A04 emits normalized messages; it does not
decide ticket workflow.
"""

from __future__ import annotations

from typing import Any

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import ConnectorUnavailable
from app.connectors.ports import (
    AttemptResult,
    CapabilityDescriptor,
    ConnectorPort,
    Evidence,
    ProviderCommand,
    payload_hash,
)
from app.core.time import utcnow
from app.services.connectors.composio_inbox import ComposioInboxConnector
from app.services.connectors.secrets import ConnectionRef

ADAPTER_VERSION = "composio-inbox-v3"
SOURCE = "inbox"


class InboxCommerceAdapter(ConnectorPort):
    """Normalized inbox read/send surface over one pinned Composio mail account."""

    def __init__(self, binding: ConnectionBinding) -> None:
        super().__init__(binding)
        # account_ref is the exact Composio connected_account_id (a reference).
        self._connector = ComposioInboxConnector(
            ConnectionRef(provider="composio", external_id=binding.account_ref)
        )
        self.descriptor = CapabilityDescriptor(
            provider=binding.provider,
            capability="inbox",
            read_operations=("messages",),
            write_operations=("send_message",),
            supports_idempotency=True,
            supports_reconciliation=False,
            sandbox=False,
        )

    async def health(self) -> dict[str, Any]:
        try:
            info = await self._connector.health()
        except Exception as exc:  # noqa: BLE001
            raise ConnectorUnavailable("inbox health probe failed") from exc
        return {
            "provider": self.binding.provider,
            "account_ref": self.binding.account_ref,
            "toolkit": info.get("toolkit", "unknown"),
            "status": info.get("status", "UNKNOWN"),
        }

    async def fetch(
        self, resource: str, *, cursor: str | None = None, limit: int = 250
    ) -> tuple[list[dict[str, Any]], str | None]:
        if resource != "messages":
            from app.connectors.errors import CapabilityUnsupported

            raise CapabilityUnsupported(f"inbox adapter cannot fetch {resource!r}")
        try:
            messages = await self._connector.list_messages(unread_only=False, limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise ConnectorUnavailable("inbox list_messages failed") from exc
        return messages, None

    async def fetch_one(self, resource: str, external_id: str) -> dict[str, Any] | None:
        # Inbox supports listing only; single-fetch is not exposed by the provider tool.
        from app.connectors.errors import CapabilityUnsupported

        raise CapabilityUnsupported("inbox adapter does not support fetch_one")

    async def execute(self, command: ProviderCommand) -> AttemptResult:
        if command.operation != "send_message":
            from app.connectors.errors import CapabilityUnsupported

            raise CapabilityUnsupported(f"inbox cannot execute {command.operation!r}")
        args = command.arguments
        sent = await self._connector.send_message(
            to=args["to"],
            subject=args.get("subject", ""),
            body=args["body"],
            in_reply_to=args.get("in_reply_to"),
        )
        op_id = str(
            sent.get("id") or sent.get("message_id") or payload_hash(command.digest())[7:19]
        )
        ev = Evidence(
            source=self.binding.provider,
            source_id=op_id,
            source_timestamp=None,
            collected_timestamp=utcnow(),
            trust_label="untrusted",
            content_hash=command.digest(),
            reference=f"{self.binding.provider}:{op_id}",
        )
        return AttemptResult(
            outcome_confidence="confirmed", provider_operation_id=op_id, evidence=[ev]
        )
