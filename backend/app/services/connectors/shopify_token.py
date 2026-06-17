"""Shopify access-token acquisition.

Preferred path (operator only provides client_id + client_secret in the dashboard):
the **client credentials grant** — the app exchanges the app's client id/secret for a
24h Admin API token with no browser, and refreshes it before expiry. Falls back to a
static `SHOPIFY_ACCESS_TOKEN` when no client creds are configured.

Requires an app developed by the operator's own org, installed in their own store
(Shopify's client-credentials precondition). Tokens are held only in process memory
and as `Secret` — never logged or persisted (Invariant 5).
"""

from __future__ import annotations

import time

import httpx

from .secrets import Secret, SecretResolutionError, env_or_setting, resolve_secret

_TIMEOUT = httpx.Timeout(30.0)
_REFRESH_MARGIN = 300  # refresh 5 min before the 24h expiry
# domain -> (token, expiry_epoch)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def _client_creds_for(domain: str) -> tuple[str, str] | None:
    """Resolve (client_id, client_secret) for a store: per-store handles first,
    then the global env names (SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET/SECRET_KEY)."""
    client_id = env_or_setting(f"SHOPIFY_CLIENT_ID:{domain}") or env_or_setting("SHOPIFY_CLIENT_ID")
    client_secret = (
        env_or_setting(f"SHOPIFY_CLIENT_SECRET:{domain}")
        or env_or_setting("SHOPIFY_CLIENT_SECRET")
        or env_or_setting("SHOPIFY_SECRET_KEY")
    )
    if client_id and client_secret:
        return client_id, client_secret
    return None


async def fetch_client_credentials_token(
    domain: str, client_id: str, client_secret: str
) -> tuple[str, int]:
    """POST the client-credentials grant; return (access_token, expires_in)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"https://{domain}/admin/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
    return str(body["access_token"]), int(body.get("expires_in", 86399))


async def get_store_token(domain: str) -> Secret:
    """Return a valid Admin API token for the store.

    Uses the client-credentials grant (cached + auto-refreshed) when client creds are
    configured; otherwise falls back to a static SHOPIFY_ACCESS_TOKEN handle.
    """
    creds = _client_creds_for(domain)
    if creds is not None:
        now = time.time()
        cached = _TOKEN_CACHE.get(domain)
        if cached is not None and cached[1] - _REFRESH_MARGIN > now:
            return Secret(cached[0])
        token, expires_in = await fetch_client_credentials_token(domain, creds[0], creds[1])
        _TOKEN_CACHE[domain] = (token, now + expires_in)
        return Secret(token)
    # Static-token fallback (per-store handle, then global).
    try:
        return resolve_secret(f"SHOPIFY_ACCESS_TOKEN:{domain}")
    except SecretResolutionError:
        return resolve_secret("SHOPIFY_ACCESS_TOKEN")
