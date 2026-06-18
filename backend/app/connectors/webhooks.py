"""Raw-body webhook signature verification + durable acceptance.

Ports the proven board-webhook discipline (HMAC over the *raw* body,
``hmac.compare_digest``) to the commerce path, and adds durable-inbox insertion
before any processing (AGENTS.md §4 / ADR-014, 05-OPS §7):

    size/content check -> verify signature on raw body -> durable insert (dedup)
    -> ack -> async normalize/process

Two signature schemes are supported: ``hex`` (GitHub-style ``sha256=<hex>``) and
``base64`` (Shopify ``X-Shopify-Hmac-Sha256``). An invalid signature never enters
the operational stream — it raises :class:`WebhookVerificationError` before the
event is persisted.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.connectors.durable import DurableInboxPort, InboundEvent
from app.connectors.errors import WebhookVerificationError
from app.connectors.models import CommerceProviderEvent
from app.connectors.ports import payload_hash

SignatureScheme = Literal["hex", "base64"]


def verify_signature(
    secret: str,
    raw_body: bytes,
    provided: str | None,
    *,
    scheme: SignatureScheme = "hex",
) -> bool:
    """Return True iff ``provided`` is a valid HMAC-SHA256 over ``raw_body``.

    Verifies against the raw bytes exactly as received — never a re-serialized body.
    """
    if not secret or not provided:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256)
    if scheme == "base64":
        expected = base64.b64encode(digest.digest()).decode("ascii")
        candidate = provided.strip()
    else:
        expected = digest.hexdigest()
        candidate = provided.strip()
        if candidate.lower().startswith("sha256="):
            candidate = candidate[7:]
        candidate = candidate.lower()
        expected = expected.lower()
    return hmac.compare_digest(candidate, expected)


@dataclass(frozen=True)
class WebhookContext:
    """Everything needed to verify and durably accept one webhook delivery."""

    source: str
    account_ref: str
    source_event_id: str
    topic: str
    secret: str
    scheme: SignatureScheme = "hex"
    occurred_at: datetime | None = None
    brand_id: UUID | None = None
    store_id: UUID | None = None
    connection_id: UUID | None = None


async def accept_webhook(
    inbox: DurableInboxPort,
    ctx: WebhookContext,
    raw_body: bytes,
    signature: str | None,
) -> tuple[CommerceProviderEvent, bool]:
    """Verify a webhook on its raw body, then durably accept it (dedup-once).

    Raises :class:`WebhookVerificationError` before any persistence if the signature
    is invalid. Returns ``(event_row, is_duplicate)``.
    """
    if not verify_signature(ctx.secret, raw_body, signature, scheme=ctx.scheme):
        raise WebhookVerificationError(
            "invalid webhook signature; rejected before processing",
            detail=f"source={ctx.source} topic={ctx.topic}",
        )
    if not ctx.source_event_id:
        # Without a provider event id we cannot dedup; refuse rather than risk
        # double-processing (I-07).
        raise WebhookVerificationError(
            "missing provider event id; cannot guarantee idempotent acceptance",
            detail=f"source={ctx.source} topic={ctx.topic}",
        )
    event = InboundEvent(
        source=ctx.source,
        source_event_id=ctx.source_event_id,
        account_ref=ctx.account_ref,
        topic=ctx.topic,
        payload_hash=payload_hash({"raw": raw_body.decode("utf-8", "replace")}),
        verification="verified",
        occurred_at=ctx.occurred_at,
        brand_id=ctx.brand_id,
        store_id=ctx.store_id,
        connection_id=ctx.connection_id,
        raw_ref=raw_body.decode("utf-8", "replace"),
    )
    return await inbox.accept(event)
