"""Vault document CRUD, retrieval, and policy seeding (Build Spec §4, §5).

Retrieval today is keyword-based (title/tag/body match) — enough for the CS agent to
cite the shipping/privacy policy. A pgvector embedding index slots in behind
`search()` without changing callers when pgvector is available.
"""

from __future__ import annotations

from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.vault import VaultDocument

# Seed fixtures required by the WISMO acceptance test (Build Spec §9a).
SEED_DOCS = [
    {
        "slug": "shipping-policy",
        "title": "Shipping Policy",
        "tags": "policy,shipping,wismo,delivery,tracking",
        "body": (
            "# Shipping Policy\n\n"
            "Orders are processed within 1-2 business days. Standard delivery takes "
            "5-8 business days within the United States.\n\n"
            "## Tracking your order\n"
            "Once your order ships you receive a tracking number by email. You can "
            "check live status any time on the tracking page linked in your order "
            "confirmation and account.\n\n"
            "If tracking has not updated for more than 3 business days, contact support "
            "and we will investigate with the carrier."
        ),
    },
    {
        "slug": "privacy-policy",
        "title": "Privacy Policy",
        "tags": "policy,privacy,data",
        "body": (
            "# Privacy Policy\n\n"
            "We collect only the information needed to fulfil and support your orders: "
            "name, email, shipping address, and order details. We never sell your data. "
            "Order and tracking information is shared only with our shipping carriers to "
            "deliver your purchase."
        ),
    },
]


async def ensure_seed_vault(session: AsyncSession, brand: Brand) -> None:
    """Seed the shipping + privacy policy docs if the vault is empty for them."""
    for doc in SEED_DOCS:
        existing = (
            await session.exec(select(VaultDocument).where(VaultDocument.slug == doc["slug"]))
        ).first()
        if existing is None:
            session.add(
                VaultDocument(
                    brand_id=brand.id,
                    slug=doc["slug"],
                    title=doc["title"],
                    tags=doc["tags"],
                    body=doc["body"],
                )
            )
    await session.commit()


async def list_documents(session: AsyncSession) -> list[VaultDocument]:
    return list((await session.exec(select(VaultDocument).order_by(VaultDocument.title))).all())


async def get_document(session: AsyncSession, slug: str) -> VaultDocument | None:
    return (
        await session.exec(select(VaultDocument).where(VaultDocument.slug == slug))
    ).first()


async def upsert_document(
    session: AsyncSession,
    *,
    brand: Brand,
    slug: str,
    title: str,
    tags: str,
    body: str,
) -> VaultDocument:
    doc = await get_document(session, slug)
    if doc is None:
        doc = VaultDocument(brand_id=brand.id, slug=slug, title=title, tags=tags, body=body)
        session.add(doc)
    else:
        doc.title = title
        doc.tags = tags
        doc.body = body
        doc.updated_at = utcnow()
        session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def search(session: AsyncSession, query: str, *, limit: int = 5) -> list[VaultDocument]:
    """Keyword retrieval over title/tags/body. (pgvector RAG slots in here later.)"""
    like = f"%{query}%"
    stmt = (
        select(VaultDocument)
        .where(
            or_(
                col(VaultDocument.title).ilike(like),
                col(VaultDocument.tags).ilike(like),
                col(VaultDocument.body).ilike(like),
            )
        )
        .limit(limit)
    )
    return list((await session.exec(stmt)).all())
