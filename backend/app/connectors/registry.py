"""Provider-independent connector resolution.

A binding resolves to a :class:`ConnectorPort` purely by ``(provider, capability)``.
The domain never names Composio or Shopify directly — they are registered adapters.
An unregistered tuple fails closed with :class:`CapabilityUnsupported` rather than
silently falling back to a default provider/account.
"""

from __future__ import annotations

from collections.abc import Callable

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import CapabilityUnsupported
from app.connectors.ports import ConnectorPort

ConnectorFactory = Callable[[ConnectionBinding], ConnectorPort]


class ConnectorRegistry:
    """Maps ``(provider, capability)`` to an adapter factory."""

    def __init__(self) -> None:
        self._factories: dict[tuple[str, str], ConnectorFactory] = {}

    def register(self, provider: str, capability: str, factory: ConnectorFactory) -> None:
        self._factories[(provider, capability)] = factory

    def supports(self, provider: str, capability: str) -> bool:
        return (provider, capability) in self._factories

    def resolve(self, binding: ConnectionBinding) -> ConnectorPort:
        factory = self._factories.get((binding.provider, binding.capability))
        if factory is None:
            raise CapabilityUnsupported(
                "no adapter registered for this provider/capability",
                detail=f"provider={binding.provider} capability={binding.capability}",
            )
        return factory(binding)


def default_registry() -> ConnectorRegistry:
    """The production registry: direct Shopify (store) + Composio (inbox).

    ``composio``/``store`` is deliberately absent until managed Shopify OAuth has a
    conformance fixture (I-19) — resolving it raises :class:`CapabilityUnsupported`,
    which is honest, rather than a generic ``NotImplementedError``.
    """
    from app.connectors.adapters.inbox import InboxCommerceAdapter
    from app.connectors.adapters.shopify import ShopifyCommerceAdapter

    reg = ConnectorRegistry()
    reg.register("direct", "store", ShopifyCommerceAdapter)
    reg.register("composio", "inbox", InboxCommerceAdapter)
    return reg
