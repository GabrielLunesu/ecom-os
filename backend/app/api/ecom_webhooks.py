"""Realtime inbound-email webhook (Build Spec §6: cron/webhooks).

Composio's OUTLOOK_MESSAGE_TRIGGER fires when a new email lands and POSTs here; we
run the CS loop immediately instead of waiting for the cron poll. This route is NOT
behind user auth (Composio can't send a bearer) — it's authenticated by a shared
secret in the URL/header. The handler returns 200 fast and runs the loop in the
background, so a slow loop never makes Composio retry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.db.session import async_session_maker
from app.events.durable import accept_inbox_event, payload_hash
from app.jobs.leased import enqueue_job
from app.services.connectors.secrets import env_or_setting

router = APIRouter(prefix="/ecom/webhooks", tags=["ecom-webhooks"])
logger = get_logger(__name__)
_REALTIME_EMAIL_SOURCE = "composio"
_REALTIME_EMAIL_SCOPE = "realtime_email"
_REALTIME_EMAIL_JOB_TYPE = "cs.realtime_email.received"


def webhook_secret() -> str:
    """Stable secret for the realtime webhook URL.

    Uses ECOM_WEBHOOK_SECRET if set, else derives a stable value from
    LOCAL_AUTH_TOKEN so the webhook works out of the box without extra config.
    """
    explicit = env_or_setting("ECOM_WEBHOOK_SECRET")
    if explicit:
        return explicit
    base = env_or_setting("LOCAL_AUTH_TOKEN")
    if not base:
        return ""
    return hashlib.sha256(f"ecom-webhook:{base}".encode()).hexdigest()[:32]


async def _run_loop() -> None:
    from app.services.cs_loop import run_cs_loop

    try:
        async with async_session_maker() as session:
            result = await run_cs_loop(session)
            logger.info("realtime.loop_done result=%s", result)
    except Exception:  # noqa: BLE001 - webhook must never crash; cron is the fallback
        logger.warning("realtime.loop_failed", exc_info=True)


@dataclass(frozen=True)
class DurableWebhookAcceptance:
    """Result of durably accepting a realtime webhook trigger."""

    event_id: str
    job_id: str
    event_created: bool
    job_created: bool


def _json_payload(raw_body: bytes) -> dict[str, Any]:
    if not raw_body:
        return {}
    try:
        value = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"raw_body_hash": payload_hash(raw_body)}
    if isinstance(value, dict):
        return value
    return {"payload": value}


def _source_event_id(request: Request, raw_body: bytes) -> str:
    for header in (
        "x-composio-event-id",
        "x-webhook-id",
        "x-ecom-event-id",
        "x-request-id",
    ):
        value = request.headers.get(header)
        if value:
            return value
    return payload_hash(raw_body)


async def persist_realtime_email_trigger(
    session: AsyncSession,
    *,
    request: Request,
    raw_body: bytes,
) -> DurableWebhookAcceptance:
    """Persist a realtime email trigger before any agent/customer-service work starts."""

    source_event_id = _source_event_id(request, raw_body)
    body_hash = payload_hash(raw_body)
    event, event_created = await accept_inbox_event(
        session,
        event_type="ticket.message.realtime_triggered",
        source=_REALTIME_EMAIL_SOURCE,
        source_scope=_REALTIME_EMAIL_SCOPE,
        source_event_id=source_event_id,
        payload=_json_payload(raw_body),
        coverage="imported",
        verification="valid",
        metadata={
            "body_hash": body_hash,
            "content_type": request.headers.get("content-type", ""),
            "path": request.url.path,
        },
    )
    job, job_created = await enqueue_job(
        session,
        job_type=_REALTIME_EMAIL_JOB_TYPE,
        payload={
            "event_id": str(event.id),
            "source": _REALTIME_EMAIL_SOURCE,
            "source_scope": _REALTIME_EMAIL_SCOPE,
            "source_event_id": source_event_id,
        },
        deduplication_key=f"{_REALTIME_EMAIL_JOB_TYPE}:{event.id}",
        trace_id=event.trace_id,
        max_attempts=3,
    )
    return DurableWebhookAcceptance(
        event_id=str(event.id),
        job_id=str(job.id),
        event_created=event_created,
        job_created=job_created,
    )


@router.api_route("/email", methods=["GET", "POST"])
async def email_webhook(request: Request, background: BackgroundTasks) -> Response:
    """Realtime trigger: a new email arrived -> run the CS loop now."""
    # GET is a connectivity/validation ping; take no action.
    if request.method == "GET":
        return Response(status_code=200)

    secret = webhook_secret()
    token = request.query_params.get("token") or request.headers.get("x-ecom-token", "")
    if not secret or token != secret:
        return Response(status_code=401)

    raw_body = await request.body()
    async with async_session_maker() as session:
        try:
            accepted = await persist_realtime_email_trigger(
                session,
                request=request,
                raw_body=raw_body,
            )
            await session.commit()
        except Exception:  # noqa: BLE001 - provider should retry; no in-memory-only acceptance.
            await session.rollback()
            logger.warning("realtime.durable_accept_failed", exc_info=True)
            return Response(status_code=503)

    if accepted.job_created:
        background.add_task(_run_loop)
    return Response(status_code=202)
