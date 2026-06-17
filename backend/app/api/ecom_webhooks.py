"""Realtime inbound-email webhook (Build Spec §6: cron/webhooks).

Composio's OUTLOOK_MESSAGE_TRIGGER fires when a new email lands and POSTs here; we
run the CS loop immediately instead of waiting for the cron poll. This route is NOT
behind user auth (Composio can't send a bearer) — it's authenticated by a shared
secret in the URL/header. The handler returns 200 fast and runs the loop in the
background, so a slow loop never makes Composio retry.
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.core.logging import get_logger
from app.db.session import async_session_maker
from app.services.connectors.secrets import env_or_setting

router = APIRouter(prefix="/ecom/webhooks", tags=["ecom-webhooks"])
logger = get_logger(__name__)


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

    background.add_task(_run_loop)
    return Response(status_code=202)
