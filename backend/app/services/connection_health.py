"""Startup connection health for the bootstrap gate (Build Spec §1.5).

Confirms Shopify and the support inbox are both live, and refuses to start the CS
loop until they are. Status payloads contain provider/status only — never secrets
(Invariant 5).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.services.connectors.composio_inbox import (
    ComposioInboxConnector,
    discover_active_mail_account,
)
from app.services.connectors.registry import shopify_connector_for
from app.services.connectors.secrets import ConnectionRef, SecretResolutionError
from app.services.connectors.shopify_direct import DirectShopifyConnector
from app.services.stores import list_stores

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProviderHealth:
    provider: str  # "shopify" | "inbox"
    connected: bool
    detail: str  # human-readable, never a secret


class CSLoopNotReady(RuntimeError):
    """Raised when the CS loop is asked to start before connections are live."""


async def check_shopify(session: AsyncSession | None = None) -> ProviderHealth:
    if session is not None:
        stores = await list_stores(session)
        if stores:
            last_error = "not connected"
            for store in stores:
                try:
                    conn = shopify_connector_for(
                        ConnectionRef(provider=store.provider, external_id=store.external_id)
                    )
                    shop = await conn.get_shop()
                except SecretResolutionError:
                    last_error = "not connected (no token)"
                    continue
                except Exception as exc:  # noqa: BLE001 - report any failure as not-connected
                    last_error = f"unreachable: {type(exc).__name__}"
                    continue
                name = shop.get("name", store.name or "unknown")
                return ProviderHealth("shopify", True, f"connected: {name}")
            return ProviderHealth("shopify", False, last_error)

    try:
        conn = DirectShopifyConnector.from_env()
        shop = await conn.get_shop()
    except SecretResolutionError:
        return ProviderHealth("shopify", False, "not connected (no token)")
    except Exception as exc:  # noqa: BLE001 - report any failure as not-connected
        return ProviderHealth("shopify", False, f"unreachable: {type(exc).__name__}")
    name = shop.get("name", "unknown")
    return ProviderHealth("shopify", True, f"connected: {name}")


async def check_inbox() -> ProviderHealth:
    try:
        account_id = await discover_active_mail_account()
    except SecretResolutionError:
        return ProviderHealth("inbox", False, "not connected (no Composio key)")
    except Exception as exc:  # noqa: BLE001
        return ProviderHealth("inbox", False, f"unreachable: {type(exc).__name__}")
    if not account_id:
        return ProviderHealth("inbox", False, "no active mail account")
    try:
        health = await ComposioInboxConnector(
            ConnectionRef(provider="composio", external_id=account_id)
        ).health()
    except Exception as exc:  # noqa: BLE001
        return ProviderHealth("inbox", False, f"unreachable: {type(exc).__name__}")
    ok = health.get("status") == "ACTIVE"
    return ProviderHealth("inbox", ok, f"{health.get('toolkit', 'mail')}: {health.get('status')}")


async def connections_status(session: AsyncSession | None = None) -> dict[str, object]:
    """Full connection report for Settings + the bootstrap gate (no secrets)."""
    shopify = await check_shopify(session) if session is not None else await check_shopify()
    inbox = await check_inbox()
    return {
        "ready": shopify.connected and inbox.connected,
        "providers": [asdict(shopify), asdict(inbox)],
    }


async def assert_ready_for_cs_loop(session: AsyncSession | None = None) -> None:
    """Gate: raise CSLoopNotReady unless both Shopify and the inbox are live."""
    shopify = await check_shopify(session) if session is not None else await check_shopify()
    inbox = await check_inbox()
    down = [p.provider for p in (shopify, inbox) if not p.connected]
    if down:
        logger.warning("CS loop blocked; providers not ready: %s", down)
        raise CSLoopNotReady(f"connections not ready: {', '.join(down)}")
