"""Concrete connector adapters behind the provider-independent ports.

Composio and direct-Shopify are *adapters*, not the ontology. New providers
register here without changing the domain contract.
"""

from __future__ import annotations

from app.connectors.adapters.fake import FakeCommerceAdapter, FakeProviderBackend

__all__ = ["FakeCommerceAdapter", "FakeProviderBackend"]
