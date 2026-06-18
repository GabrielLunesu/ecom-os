"""Normalized commerce read models + local durable inbox/action stand-ins.

All tables share the global ``SQLModel.metadata`` (via :class:`QueryModel`).

Cross-cutting contract (BUILD §4 / 04-DATA §5.5): every normalized row records its
``source``, opaque provider ``external_id`` (kept separate from the internal id),
``source_updated_at`` (upstream version time), ``synced_at`` (collected time), and a
``coverage`` label. Money is stored as integer minor units plus an ISO currency (I-16).

The ``CommerceProviderEvent`` (durable inbox), ``CommerceAction`` and
``CommerceActionAttempt`` tables are **local stand-ins for the A02 durable
event/action ports** so A04 can build and test the full vertical before A02 lands.
They implement the same uniqueness/idempotency guarantees and are swapped for A02's
canonical tables at integration (see INTERFACES.md IR-A04-01).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field

from app.core.time import utcnow
from app.models.base import QueryModel

# --- connection records -----------------------------------------------------


class Connection(QueryModel, table=True):
    """A first-class connector connection bound to one exact account.

    Decoupled from ``Store`` so a store can carry multiple connections (store/inbox/
    ads) and each pins its own exact account (I-09). Holds references only — for
    direct adapters ``secret_handle`` is a non-secret handle into the secret store;
    for managed providers it is empty and ``account_ref`` is the provider account id
    (I-15).
    """

    __tablename__ = "commerce_connections"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "store_id", "capability", "account_ref", name="uq_connection_store_cap_account"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(index=True)
    store_id: UUID = Field(index=True)
    provider: str = Field(default="direct")
    capability: str = Field(default="store", index=True)
    account_ref: str = Field(default="")
    secret_handle: str = Field(default="")
    adapter_version: str = Field(default="v1")
    status: str = Field(default="disconnected", index=True)
    last_health_at: datetime | None = Field(default=None)
    last_health_ok: bool = Field(default=False)
    last_health_detail: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# --- normalized commerce entities -------------------------------------------


class Customer(QueryModel, table=True):
    __tablename__ = "commerce_customers"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("store_id", "source", "external_id", name="uq_customer_source_ext"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    store_id: UUID = Field(index=True)
    source: str = Field(default="")
    external_id: str = Field(default="", index=True)
    email: str = Field(default="", index=True)
    name: str = Field(default="")
    orders_count: int = Field(default=0)
    source_updated_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utcnow)
    coverage: str = Field(default="imported")

    def to_view(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "email": self.email,
            "name": self.name,
            "orders_count": self.orders_count,
            "source": self.source,
            "source_updated_at": (
                self.source_updated_at.isoformat() if self.source_updated_at else None
            ),
        }


class Order(QueryModel, table=True):
    __tablename__ = "commerce_orders"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("store_id", "source", "external_id", name="uq_order_source_ext"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    store_id: UUID = Field(index=True)
    customer_id: UUID | None = Field(default=None, index=True)
    source: str = Field(default="")
    external_id: str = Field(default="", index=True)
    order_number: str = Field(default="", index=True)  # e.g. "#1001"
    email: str = Field(default="", index=True)
    currency: str = Field(default="USD")
    total_minor: int = Field(default=0)
    subtotal_minor: int = Field(default=0)
    financial_status: str = Field(default="")
    fulfillment_status: str = Field(default="")
    placed_at: datetime | None = Field(default=None)
    source_updated_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utcnow)
    coverage: str = Field(default="imported")
    primary_trace_id: str = Field(default="")

    def to_view(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "order_number": self.order_number,
            "email": self.email,
            "currency": self.currency,
            "total_minor": self.total_minor,
            "subtotal_minor": self.subtotal_minor,
            "financial_status": self.financial_status,
            "fulfillment_status": self.fulfillment_status,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
            "source": self.source,
            "source_updated_at": (
                self.source_updated_at.isoformat() if self.source_updated_at else None
            ),
        }


class OrderLine(QueryModel, table=True):
    __tablename__ = "commerce_order_lines"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("order_id", "external_id", name="uq_order_line_ext"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(index=True)
    external_id: str = Field(default="")
    title: str = Field(default="")
    sku: str = Field(default="")
    quantity: int = Field(default=0)
    price_minor: int = Field(default=0)
    product_external_id: str = Field(default="")

    def to_view(self) -> dict[str, object]:
        return {
            "title": self.title,
            "sku": self.sku,
            "quantity": self.quantity,
            "price_minor": self.price_minor,
        }


class Product(QueryModel, table=True):
    __tablename__ = "commerce_products"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("store_id", "source", "external_id", name="uq_product_source_ext"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    store_id: UUID = Field(index=True)
    source: str = Field(default="")
    external_id: str = Field(default="", index=True)
    title: str = Field(default="")
    status: str = Field(default="")
    source_updated_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utcnow)
    coverage: str = Field(default="imported")


class Fulfillment(QueryModel, table=True):
    __tablename__ = "commerce_fulfillments"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("order_id", "source", "external_id", name="uq_fulfillment_source_ext"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(index=True)
    source: str = Field(default="")
    external_id: str = Field(default="")
    status: str = Field(default="")
    tracking_company: str = Field(default="")
    tracking_number: str = Field(default="")
    tracking_url: str = Field(default="")
    shipped_at: datetime | None = Field(default=None)
    source_updated_at: datetime | None = Field(default=None)
    synced_at: datetime = Field(default_factory=utcnow)

    def to_view(self) -> dict[str, object]:
        return {
            "status": self.status,
            "tracking_company": self.tracking_company,
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
        }


class ProviderRef(QueryModel, table=True):
    """Opaque upstream identifiers kept separate from internal ids (04-DATA §3).

    Never use an external id alone as a global identifier; this table is the scoped
    bridge between an internal entity and its provider id/version.
    """

    __tablename__ = "commerce_provider_refs"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "source", name="uq_provider_ref_entity"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    entity_type: str = Field(index=True)  # order|customer|product|fulfillment
    entity_id: UUID = Field(index=True)
    source: str = Field(default="")
    connection_id: UUID | None = Field(default=None)
    external_id: str = Field(default="")
    external_version: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)


class SyncCursor(QueryModel, table=True):
    """Incremental-sync watermark per (connection, resource)."""

    __tablename__ = "commerce_sync_cursors"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("connection_id", "resource", name="uq_sync_cursor_conn_resource"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    connection_id: UUID = Field(index=True)
    resource: str = Field(default="")
    cursor: str = Field(default="")
    last_synced_at: datetime | None = Field(default=None)
    last_status: str = Field(default="")


# --- local stand-ins for the A02 durable ports ------------------------------


class CommerceProviderEvent(QueryModel, table=True):
    """Durable inbox row (A02 stand-in).

    A unique ``(source, account_ref, source_event_id)`` enforces that a duplicate
    webhook/provider delivery is accepted exactly once (I-07, AGENTS.md §4). The raw
    event is verified and persisted BEFORE any processing.
    """

    __tablename__ = "commerce_provider_events"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "source", "account_ref", "source_event_id", name="uq_provider_event_identity"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID | None = Field(default=None)
    store_id: UUID | None = Field(default=None)
    connection_id: UUID | None = Field(default=None)
    source: str = Field(default="", index=True)
    source_event_id: str = Field(default="")
    account_ref: str = Field(default="")
    topic: str = Field(default="")
    payload_hash: str = Field(default="")
    verification: str = Field(default="")  # verified|unverified
    occurred_at: datetime | None = Field(default=None)
    received_at: datetime = Field(default_factory=utcnow)
    processing_state: str = Field(default="received", index=True)
    raw_ref: str = Field(default="", sa_column=Column(Text))


class CommerceAction(QueryModel, table=True):
    """Durable external-write action (A02 stand-in).

    Unique ``idempotency_intent_key`` makes the intent idempotent regardless of
    provider idempotency support (I-07, 04-DATA §8.4). ``state`` follows the action
    state machine incl. ``outcome_unknown`` (04-DATA §8.2).
    """

    __tablename__ = "commerce_actions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("idempotency_intent_key", name="uq_action_intent_key"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(index=True)
    store_id: UUID = Field(index=True)
    connection_id: UUID = Field(index=True)
    action_type: str = Field(default="")
    target: str = Field(default="")
    arguments_json: str = Field(default="{}", sa_column=Column(Text))
    currency: str = Field(default="")
    amount_minor: int = Field(default=0)
    digest: str = Field(default="")
    idempotency_intent_key: str = Field(default="")
    grant_mode: str = Field(default="")
    state: str = Field(default="proposed", index=True)
    provider_operation_id: str | None = Field(default=None)
    outcome_summary: str = Field(default="")
    reconcile_due_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CommerceActionAttempt(QueryModel, table=True):
    """Append-only connector attempt record (A02 stand-in, 04-DATA §8.3)."""

    __tablename__ = "commerce_action_attempts"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    action_id: UUID = Field(index=True)
    attempt_number: int = Field(default=1)
    connector: str = Field(default="")
    account_ref: str = Field(default="")
    provider_idempotency_key: str = Field(default="")
    request_fingerprint: str = Field(default="")
    provider_operation_id: str | None = Field(default=None)
    status_category: str = Field(default="")
    outcome_confidence: str = Field(default="unknown")
    retry_classification: str = Field(default="")
    summary_json: str = Field(default="{}", sa_column=Column(Text))
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = Field(default=None)
    reconcile_due_at: datetime | None = Field(default=None)
