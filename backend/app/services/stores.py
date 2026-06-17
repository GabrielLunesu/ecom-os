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
            session.add(
                Store(
                    brand_id=brand.id,
                    name=domain.split(".")[0].replace("-", " ").title(),
                    domain=domain,
                    provider="direct",
                    external_id=domain,  # ref, not a secret
                    status="connected" if connected else "disconnected",
                )
            )
    await session.commit()
    return brand


async def list_stores(session: AsyncSession) -> list[Store]:
    return list((await session.exec(select(Store).order_by(Store.name))).all())
