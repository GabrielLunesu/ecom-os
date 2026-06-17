"""Dashboard-managed encrypted secrets (Invariant 5).

The operator sets connection keys from the dashboard; the value is encrypted at
rest (Fernet) and NEVER returned in plaintext. Only the *handle* (a name, e.g.
"COMPOSIO_API_KEY" or "SHOPIFY_ACCESS_TOKEN:store.myshopify.com") is ever exposed.

Invariant 1 in spirit: connectors resolve their values from here, the secure home
for the credential, rather than the row carrying a raw token in the open.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class SecretEntry(QueryModel, table=True):
    """One encrypted secret, addressed by a non-secret handle."""

    __tablename__ = "secret_entries"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    # Non-secret name, e.g. "COMPOSIO_API_KEY" or
    # "SHOPIFY_ACCESS_TOKEN:store.myshopify.com".
    handle: str = Field(index=True, unique=True)
    # Fernet ciphertext — never the plaintext (Invariant 5).
    ciphertext: str = Field(sa_column=Column(Text, nullable=False))
    updated_at: datetime = Field(default_factory=utcnow)
