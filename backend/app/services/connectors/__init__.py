"""Provider connectors for Ecom-OS (Shopify + support inbox).

Public surface is intentionally small. The CS agent only ever receives a
`ShopifyConnector` (read + discounts) — never the `RefundExecutor` (Invariant 2).
"""

from __future__ import annotations

from .base import InboxConnector, ShopifyConnector
from .refunds import RefundApproval, RefundExecutor, RefundNotApprovedError
from .registry import shopify_connector_for
from .secrets import (
    ConnectionRef,
    Secret,
    SecretResolutionError,
    resolve_secret,
)
from .shopify_direct import DirectShopifyConnector

__all__ = [
    "ConnectionRef",
    "DirectShopifyConnector",
    "InboxConnector",
    "RefundApproval",
    "RefundExecutor",
    "RefundNotApprovedError",
    "Secret",
    "SecretResolutionError",
    "ShopifyConnector",
    "resolve_secret",
    "shopify_connector_for",
]
