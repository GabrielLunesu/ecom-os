"""Direct Shopify Admin API connector.

Used because Composio's managed Shopify OAuth was unavailable for this brand. The
offline Admin API token is resolved from the server environment as a `Secret` and
revealed only when building the request header (Invariant 5). Swappable with a
future `ComposioShopifyConnector` behind the `ShopifyConnector` interface.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import ShopifyConnector
from .secrets import ConnectionRef, env_or_setting, resolve_secret

API_VERSION = "2025-01"
TOKEN_HANDLE = "SHOPIFY_ACCESS_TOKEN"
_TIMEOUT = httpx.Timeout(30.0)


class DirectShopifyConnector(ShopifyConnector):
    """Talk to one store's Admin REST API with a direct offline token."""

    def __init__(self, ref: ConnectionRef) -> None:
        super().__init__(ref)
        # ref.external_id is the (non-secret) store domain, e.g. *.myshopify.com.
        self._domain = ref.external_id
        self._token = resolve_secret(TOKEN_HANDLE)

    @classmethod
    def from_env(cls) -> "DirectShopifyConnector":
        domain = env_or_setting("SHOPIFY_STORE_URL")
        if not domain:
            raise RuntimeError("SHOPIFY_STORE_URL is not set")
        return cls(ConnectionRef(provider="direct", external_id=domain))

    def _client(self) -> httpx.AsyncClient:
        # The token is revealed only here, into the request header.
        return httpx.AsyncClient(
            base_url=f"https://{self._domain}/admin/api/{API_VERSION}",
            headers={
                "X-Shopify-Access-Token": self._token.reveal(),
                "Content-Type": "application/json",
            },
            timeout=_TIMEOUT,
        )

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.get(path, params=params)
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
            return body

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._client() as client:
            resp = await client.post(path, json=payload)
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
            return body

    # --- reads -------------------------------------------------------------
    async def get_shop(self) -> dict[str, Any]:
        data = await self._get("/shop.json")
        shop: dict[str, Any] = data.get("shop", {})
        return shop

    async def get_order(self, order_id: str) -> dict[str, Any]:
        data = await self._get(f"/orders/{order_id}.json")
        order: dict[str, Any] = data.get("order", {})
        return order

    async def search_orders(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"status": "any", "limit": limit}
        if "@" in query:
            params["email"] = query
        else:
            params["name"] = query
        data = await self._get("/orders.json", params=params)
        orders: list[dict[str, Any]] = data.get("orders", [])
        return orders

    async def get_fulfillments(self, order_id: str) -> list[dict[str, Any]]:
        data = await self._get(f"/orders/{order_id}/fulfillments.json")
        fulfillments: list[dict[str, Any]] = data.get("fulfillments", [])
        return fulfillments

    # --- discounts ---------------------------------------------------------
    async def create_discount(
        self, *, title: str, percentage: float, code: str
    ) -> dict[str, Any]:
        # A percentage price rule + a discount code referencing it.
        rule = await self._post(
            "/price_rules.json",
            {
                "price_rule": {
                    "title": title,
                    "target_type": "line_item",
                    "target_selection": "all",
                    "allocation_method": "across",
                    "value_type": "percentage",
                    "value": f"-{abs(percentage)}",
                    "customer_selection": "all",
                    "starts_at": None,
                }
            },
        )
        rule_id = rule["price_rule"]["id"]
        dc = await self._post(
            f"/price_rules/{rule_id}/discount_codes.json",
            {"discount_code": {"code": code}},
        )
        return {"price_rule": rule["price_rule"], "discount_code": dc["discount_code"]}
