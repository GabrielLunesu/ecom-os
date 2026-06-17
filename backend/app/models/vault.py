"""Vault: Obsidian-style markdown documents the agents read (Build Spec §4).

Each document is a markdown file with a slug + tags. The embedding index (pgvector)
for semantic RAG is added when pgvector is available; retrieval today is by slug/tag,
which is all the WISMO SOP needs to cite the shipping/privacy policy.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel


class VaultDocument(QueryModel, table=True):
    """A markdown document in the brand vault."""

    __tablename__ = "vault_documents"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brands.id", index=True)
    slug: str = Field(index=True, unique=True)  # e.g. "shipping-policy"
    title: str = Field(index=True)
    # Comma-separated tags for retrieval (e.g. "policy,shipping,wismo").
    tags: str = Field(default="")
    body: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
