"""A04 — provider-independent commerce connector layer (v2 canonical).

This package supersedes the Shopify-shaped prototype in
``app/services/connectors`` by introducing a provider-independent contract:

- :mod:`app.connectors.errors` — typed connector errors (fail closed, redacted).
- :mod:`app.connectors.binding` — :class:`ConnectionBinding` with exact
  brand/store/connection/account binding (Invariant I-09).
- :mod:`app.connectors.ports` — coverage/freshness/evidence value types and the
  :class:`ConnectorPort` read/execute/reconcile contract.
- :mod:`app.connectors.registry` — provider-independent connector resolution.
- :mod:`app.connectors.adapters` — concrete adapters (Composio is one adapter,
  not the ontology).
- :mod:`app.connectors.models` — normalized commerce read models + the local
  durable inbox/action stand-ins for the A02 ports.

Importing this package registers the commerce SQLModel tables onto the shared
``SQLModel.metadata`` so tests and migrations can build them.
"""

from __future__ import annotations

from app.connectors import models as models  # noqa: F401  (register table metadata)

__all__ = ["models"]
