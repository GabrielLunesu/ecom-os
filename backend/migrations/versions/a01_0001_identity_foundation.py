"""a01 identity foundation: roles, permissions, service & channel identities, bootstrap

Revision ID: a01_0001_identity
Revises: a0b1c2d3e4f5
Create Date: 2026-06-19 00:00:00.000000

Owner: A01 (platform foundation). Adds the v2 instance-identity tables alongside the
existing prototype schema; it does not alter or drop any existing table. Idempotent
create-if-absent guards keep it safe to re-run (init_db startup migrate, CI).
"""

from __future__ import annotations

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a01_0001_identity"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None

_TABLES = (
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "service_identities",
    "channel_identities",
    "platform_bootstrap",
)


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _str() -> sa.types.TypeEngine[str]:
    return sqlmodel.sql.sqltypes.AutoString()


def upgrade() -> None:
    if not _has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", _str(), nullable=False),
            sa.Column("description", _str(), nullable=False, server_default=""),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    if not _has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("key", _str(), nullable=False),
            sa.Column("description", _str(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )
        op.create_index("ix_permissions_key", "permissions", ["key"], unique=True)

    if not _has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("role_id", sa.Uuid(), nullable=False),
            sa.Column("permission_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "role_id",
                "permission_id",
                name="uq_role_permissions_role_perm",
            ),
        )
        op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
        op.create_index(
            "ix_role_permissions_permission_id",
            "role_permissions",
            ["permission_id"],
        )

    if not _has_table("user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("role_id", sa.Uuid(), nullable=False),
            sa.Column("granted_at", sa.DateTime(), nullable=False),
            sa.Column("granted_by_user_id", sa.Uuid(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
            sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        )
        op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
        op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    if not _has_table("service_identities"):
        op.create_table(
            "service_identities",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", _str(), nullable=False),
            sa.Column("audience", _str(), nullable=False, server_default=""),
            sa.Column("scopes", _str(), nullable=False, server_default=""),
            sa.Column("token_selector", _str(), nullable=False),
            sa.Column("token_hash", _str(), nullable=False, server_default=""),
            sa.Column("status", _str(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("rotated_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
            sa.UniqueConstraint("token_selector"),
        )
        op.create_index("ix_service_identities_name", "service_identities", ["name"], unique=True)
        op.create_index(
            "ix_service_identities_token_selector",
            "service_identities",
            ["token_selector"],
            unique=True,
        )
        op.create_index("ix_service_identities_status", "service_identities", ["status"])

    if not _has_table("channel_identities"):
        op.create_table(
            "channel_identities",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("platform", _str(), nullable=False),
            sa.Column("platform_account", _str(), nullable=False, server_default=""),
            sa.Column("platform_user_id", _str(), nullable=False),
            sa.Column("chat_id", _str(), nullable=True),
            sa.Column("channel_id", _str(), nullable=True),
            sa.Column("role_snapshot", _str(), nullable=False, server_default=""),
            sa.Column("status", _str(), nullable=False, server_default="active"),
            sa.Column("hermes_profile_id", _str(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "platform",
                "platform_account",
                "platform_user_id",
                name="uq_channel_identities_platform_user",
            ),
        )
        op.create_index("ix_channel_identities_user_id", "channel_identities", ["user_id"])
        op.create_index("ix_channel_identities_platform", "channel_identities", ["platform"])
        op.create_index(
            "ix_channel_identities_platform_user_id",
            "channel_identities",
            ["platform_user_id"],
        )
        op.create_index("ix_channel_identities_status", "channel_identities", ["status"])

    if not _has_table("platform_bootstrap"):
        op.create_table(
            "platform_bootstrap",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("singleton", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", _str(), nullable=False, server_default="open"),
            sa.Column("owner_user_id", sa.Uuid(), nullable=True),
            sa.Column("opened_at", sa.DateTime(), nullable=False),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("singleton"),
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        if _has_table(table):
            op.drop_table(table)
