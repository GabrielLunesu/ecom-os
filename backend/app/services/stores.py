"""Brand + store provisioning and lookup.

Single-tenant: one brand row, seeded from the environment on first use along with
the store(s) configured for this deployment. Stores carry connection refs only
(Invariant 1); secrets are never written here.
"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.brand import Brand, Store
from app.services.connectors.secrets import env_or_setting

DEFAULT_BRAND_NAME = "Chicago Outlet"


async def ensure_seed(session: AsyncSession) -> Brand:
    """Create the brand and the env-configured store if they don't exist yet."""
    brand = (await session.exec(select(Brand))).first()
    if brand is None:
        brand = Brand(name=DEFAULT_BRAND_NAME)
        session.add(brand)
        await session.flush()

    domain = env_or_setting("SHOPIFY_STORE_URL").strip()
    if domain:
        existing = (
            await session.exec(select(Store).where(Store.domain == domain))
        ).first()
        if existing is None:
            connected = bool(env_or_setting("SHOPIFY_ACCESS_TOKEN").strip())
            name = await _resolve_store_name(domain, connected)
            session.add(
                Store(
                    brand_id=brand.id,
                    name=name,
                    domain=domain,
                    provider="direct",
                    external_id=domain,  # ref, not a secret
                    status="connected" if connected else "disconnected",
                )
            )
    await session.commit()
    return brand


async def _resolve_store_name(domain: str, connected: bool) -> str:
    """Best-effort: use the live Shopify shop name; fall back to the domain slug."""
    fallback = domain.split(".")[0].replace("-", " ").title()
    if not connected:
        return fallback
    try:
        from app.services.connectors.registry import shopify_connector_for
        from app.services.connectors.secrets import ConnectionRef

        conn = shopify_connector_for(ConnectionRef(provider="direct", external_id=domain))
        shop = await conn.get_shop()
        return str(shop.get("name") or fallback).title()
    except Exception:  # noqa: BLE001 - seeding must never fail on a network hiccup
        return fallback


async def list_stores(session: AsyncSession) -> list[Store]:
    return list((await session.exec(select(Store).order_by(Store.name))).all())
