"""A04: add normalized commerce models + durable inbox/action stand-ins

Revision ID: a04commerce01
Revises: a0b1c2d3e4f5
Create Date: 2026-06-19 00:00:00.000000

Owned by A04 (commerce connectors). Creates the normalized read model
(connections/orders/order_lines/customers/products/fulfillments/provider_refs/
sync_cursors) plus the local stand-ins for the A02 durable inbox/action ports
(provider_events/actions/action_attempts). All DDL is guarded so the migration is
idempotent on partially-initialized databases (repo convention).
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a04commerce01"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None

_STR = sqlmodel.sql.sqltypes.AutoString

# Tables in dependency-free creation order; dropped in reverse on downgrade.
_TABLES = [
    "commerce_connections",
    "commerce_customers",
    "commerce_orders",
    "commerce_order_lines",
    "commerce_products",
    "commerce_fulfillments",
    "commerce_provider_refs",
    "commerce_sync_cursors",
    "commerce_provider_events",
    "commerce_actions",
    "commerce_action_attempts",
]


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("commerce_connections"):
        op.create_table(
            "commerce_connections",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("provider", _STR(), nullable=False),
            sa.Column("capability", _STR(), nullable=False),
            sa.Column("account_ref", _STR(), nullable=False),
            sa.Column("secret_handle", _STR(), nullable=False),
            sa.Column("adapter_version", _STR(), nullable=False),
            sa.Column("status", _STR(), nullable=False),
            sa.Column("last_health_at", sa.DateTime(), nullable=True),
            sa.Column("last_health_ok", sa.Boolean(), nullable=False),
            sa.Column("last_health_detail", _STR(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "store_id",
                "capability",
                "account_ref",
                name="uq_connection_store_cap_account",
            ),
        )
        op.create_index("ix_commerce_connections_brand_id", "commerce_connections", ["brand_id"])
        op.create_index("ix_commerce_connections_store_id", "commerce_connections", ["store_id"])
        op.create_index(
            "ix_commerce_connections_capability", "commerce_connections", ["capability"]
        )
        op.create_index("ix_commerce_connections_status", "commerce_connections", ["status"])

    if not _has_table("commerce_customers"):
        op.create_table(
            "commerce_customers",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("email", _STR(), nullable=False),
            sa.Column("name", _STR(), nullable=False),
            sa.Column("orders_count", sa.Integer(), nullable=False),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("coverage", _STR(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("store_id", "source", "external_id", name="uq_customer_source_ext"),
        )
        op.create_index("ix_commerce_customers_store_id", "commerce_customers", ["store_id"])
        op.create_index("ix_commerce_customers_external_id", "commerce_customers", ["external_id"])
        op.create_index("ix_commerce_customers_email", "commerce_customers", ["email"])

    if not _has_table("commerce_orders"):
        op.create_table(
            "commerce_orders",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("customer_id", sa.Uuid(), nullable=True),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("order_number", _STR(), nullable=False),
            sa.Column("email", _STR(), nullable=False),
            sa.Column("currency", _STR(), nullable=False),
            sa.Column("total_minor", sa.Integer(), nullable=False),
            sa.Column("subtotal_minor", sa.Integer(), nullable=False),
            sa.Column("financial_status", _STR(), nullable=False),
            sa.Column("fulfillment_status", _STR(), nullable=False),
            sa.Column("placed_at", sa.DateTime(), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("coverage", _STR(), nullable=False),
            sa.Column("primary_trace_id", _STR(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("store_id", "source", "external_id", name="uq_order_source_ext"),
        )
        op.create_index("ix_commerce_orders_store_id", "commerce_orders", ["store_id"])
        op.create_index("ix_commerce_orders_customer_id", "commerce_orders", ["customer_id"])
        op.create_index("ix_commerce_orders_external_id", "commerce_orders", ["external_id"])
        op.create_index("ix_commerce_orders_order_number", "commerce_orders", ["order_number"])
        op.create_index("ix_commerce_orders_email", "commerce_orders", ["email"])

    if not _has_table("commerce_order_lines"):
        op.create_table(
            "commerce_order_lines",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("order_id", sa.Uuid(), nullable=False),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("title", _STR(), nullable=False),
            sa.Column("sku", _STR(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("price_minor", sa.Integer(), nullable=False),
            sa.Column("product_external_id", _STR(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_id", "external_id", name="uq_order_line_ext"),
        )
        op.create_index("ix_commerce_order_lines_order_id", "commerce_order_lines", ["order_id"])

    if not _has_table("commerce_products"):
        op.create_table(
            "commerce_products",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("title", _STR(), nullable=False),
            sa.Column("status", _STR(), nullable=False),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.Column("coverage", _STR(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("store_id", "source", "external_id", name="uq_product_source_ext"),
        )
        op.create_index("ix_commerce_products_store_id", "commerce_products", ["store_id"])
        op.create_index("ix_commerce_products_external_id", "commerce_products", ["external_id"])

    if not _has_table("commerce_fulfillments"):
        op.create_table(
            "commerce_fulfillments",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("order_id", sa.Uuid(), nullable=False),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("status", _STR(), nullable=False),
            sa.Column("tracking_company", _STR(), nullable=False),
            sa.Column("tracking_number", _STR(), nullable=False),
            sa.Column("tracking_url", _STR(), nullable=False),
            sa.Column("shipped_at", sa.DateTime(), nullable=True),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("synced_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "order_id", "source", "external_id", name="uq_fulfillment_source_ext"
            ),
        )
        op.create_index("ix_commerce_fulfillments_order_id", "commerce_fulfillments", ["order_id"])

    if not _has_table("commerce_provider_refs"):
        op.create_table(
            "commerce_provider_refs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("entity_type", _STR(), nullable=False),
            sa.Column("entity_id", sa.Uuid(), nullable=False),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("connection_id", sa.Uuid(), nullable=True),
            sa.Column("external_id", _STR(), nullable=False),
            sa.Column("external_version", _STR(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "entity_type", "entity_id", "source", name="uq_provider_ref_entity"
            ),
        )
        op.create_index(
            "ix_commerce_provider_refs_entity_type", "commerce_provider_refs", ["entity_type"]
        )
        op.create_index(
            "ix_commerce_provider_refs_entity_id", "commerce_provider_refs", ["entity_id"]
        )

    if not _has_table("commerce_sync_cursors"):
        op.create_table(
            "commerce_sync_cursors",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("connection_id", sa.Uuid(), nullable=False),
            sa.Column("resource", _STR(), nullable=False),
            sa.Column("cursor", _STR(), nullable=False),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("last_status", _STR(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "resource", name="uq_sync_cursor_conn_resource"),
        )
        op.create_index(
            "ix_commerce_sync_cursors_connection_id", "commerce_sync_cursors", ["connection_id"]
        )

    if not _has_table("commerce_provider_events"):
        op.create_table(
            "commerce_provider_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=True),
            sa.Column("store_id", sa.Uuid(), nullable=True),
            sa.Column("connection_id", sa.Uuid(), nullable=True),
            sa.Column("source", _STR(), nullable=False),
            sa.Column("source_event_id", _STR(), nullable=False),
            sa.Column("account_ref", _STR(), nullable=False),
            sa.Column("topic", _STR(), nullable=False),
            sa.Column("payload_hash", _STR(), nullable=False),
            sa.Column("verification", _STR(), nullable=False),
            sa.Column("occurred_at", sa.DateTime(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=False),
            sa.Column("processing_state", _STR(), nullable=False),
            sa.Column("raw_ref", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source", "account_ref", "source_event_id", name="uq_provider_event_identity"
            ),
        )
        op.create_index(
            "ix_commerce_provider_events_source", "commerce_provider_events", ["source"]
        )
        op.create_index(
            "ix_commerce_provider_events_processing_state",
            "commerce_provider_events",
            ["processing_state"],
        )

    if not _has_table("commerce_actions"):
        op.create_table(
            "commerce_actions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("brand_id", sa.Uuid(), nullable=False),
            sa.Column("store_id", sa.Uuid(), nullable=False),
            sa.Column("connection_id", sa.Uuid(), nullable=False),
            sa.Column("action_type", _STR(), nullable=False),
            sa.Column("target", _STR(), nullable=False),
            sa.Column("arguments_json", sa.Text(), nullable=False),
            sa.Column("currency", _STR(), nullable=False),
            sa.Column("amount_minor", sa.Integer(), nullable=False),
            sa.Column("digest", _STR(), nullable=False),
            sa.Column("idempotency_intent_key", _STR(), nullable=False),
            sa.Column("grant_mode", _STR(), nullable=False),
            sa.Column("state", _STR(), nullable=False),
            sa.Column("provider_operation_id", _STR(), nullable=True),
            sa.Column("outcome_summary", _STR(), nullable=False),
            sa.Column("reconcile_due_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_intent_key", name="uq_action_intent_key"),
        )
        op.create_index("ix_commerce_actions_brand_id", "commerce_actions", ["brand_id"])
        op.create_index("ix_commerce_actions_store_id", "commerce_actions", ["store_id"])
        op.create_index("ix_commerce_actions_connection_id", "commerce_actions", ["connection_id"])
        op.create_index("ix_commerce_actions_state", "commerce_actions", ["state"])

    if not _has_table("commerce_action_attempts"):
        op.create_table(
            "commerce_action_attempts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("action_id", sa.Uuid(), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("connector", _STR(), nullable=False),
            sa.Column("account_ref", _STR(), nullable=False),
            sa.Column("provider_idempotency_key", _STR(), nullable=False),
            sa.Column("request_fingerprint", _STR(), nullable=False),
            sa.Column("provider_operation_id", _STR(), nullable=True),
            sa.Column("status_category", _STR(), nullable=False),
            sa.Column("outcome_confidence", _STR(), nullable=False),
            sa.Column("retry_classification", _STR(), nullable=False),
            sa.Column("summary_json", sa.Text(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("reconcile_due_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_commerce_action_attempts_action_id", "commerce_action_attempts", ["action_id"]
        )


def downgrade() -> None:
    # Dropping each table also drops its indexes/constraints.
    for name in reversed(_TABLES):
        if _has_table(name):
            op.drop_table(name)
