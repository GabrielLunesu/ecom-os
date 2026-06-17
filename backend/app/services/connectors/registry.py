"""Connector factory — resolves a stored ConnectionRef to a live connector.

Keeps the rest of the app provider-agnostic (Build Spec §6, swappable runtime).
Returns connectors built from refs only; raw secrets are resolved internally.
"""

from __future__ import annotations

from .base import ShopifyConnector
from .secrets import ConnectionRef
from .shopify_direct import DirectShopifyConnector


def shopify_connector_for(ref: ConnectionRef) -> ShopifyConnector:
    """Build the Shopify connector for a store's connection reference."""
    if ref.provider == "direct":
        return DirectShopifyConnector(ref)
    if ref.provider == "composio":
        # ComposioShopifyConnector lands when Composio's Shopify OAuth is available.
        raise NotImplementedError(
            "Composio Shopify connector not yet wired; using direct provider",
        )
    raise ValueError(f"unsupported provider: {ref.provider!r}")
