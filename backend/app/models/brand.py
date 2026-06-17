"""Brand and Store models — the single-tenant brand and its many Shopify stores.

Build Spec §1/§4: one brand, many stores. A store row holds only a *connection
reference* (provider + external id), never raw credentials (Invariant 1). The
secret is resolved server-side from the environment/secret store at call time.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class Brand(QueryModel, table=True):
    """The single brand this deployment serves (one row)."""

    __tablename__ = "brands"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    # Free-form branding/runtime config (logo, accent, runtime selection) — no secrets.
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Store(QueryModel, table=True):
    """A Shopify store belonging to the brand. Holds a connection ref only."""

    __tablename__ = "stores"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    name: str = Field(index=True)
    domain: str = Field(index=True, unique=True)  # *.myshopify.com

    # Connection reference (Invariant 1): provider in {"composio","direct"} and the
    # external id (Composio connected_account_id, or env handle/domain for direct).
    # NEVER a token.
    provider: str = Field(default="direct")
    external_id: str = Field(default="")
    status: str = Field(default="disconnected", index=True)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
