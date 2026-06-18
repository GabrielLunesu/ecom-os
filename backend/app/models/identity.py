"""V2 identity model: instance roles/permissions, service & channel identities.

Normative basis: `01-ARCHITECTURE.md` §16, `04-DATA-AND-TRACEABILITY.md` §5.1,
`05-OPERATIONS-AND-SECURITY.md` §3. ADR-001 makes the instance single-brand, so roles
here are **instance-level** (owner/admin/operator/…), distinct from the prototype's
org-scoped `OrganizationMember.role` (which is retained for board features). This is an
identity/permission primitive layer, not a second business-authorization engine.

New tables use UUIDv7 primary keys (sortable; AGENTS.md §6). Timestamps follow the
existing prototype convention (naive UTC via :func:`app.core.time.utcnow`) so they
match sibling columns; v2 tz-aware helpers exist for presentation boundaries.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.ids import uuid7
from app.core.time import utcnow
from app.models.base import QueryModel

# --- Status / role / scope constants ---------------------------------------------

IDENTITY_STATUS_ACTIVE = "active"
IDENTITY_STATUS_REVOKED = "revoked"

BOOTSTRAP_OPEN = "open"
BOOTSTRAP_CLOSED = "closed"

# Minimum instance roles (01-ARCHITECTURE §16). Seeded as system roles.
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_CS_LEAD = "cs_lead"
ROLE_CS_REP = "cs_rep"
ROLE_FINANCE = "finance"
ROLE_VIEWER = "viewer"

SYSTEM_ROLES = (
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_CS_LEAD,
    ROLE_CS_REP,
    ROLE_FINANCE,
    ROLE_VIEWER,
)


class Role(QueryModel, table=True):
    """An instance-level role (e.g. ``owner``, ``admin``)."""

    __tablename__ = "roles"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str = Field(default="")
    is_system: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)


class Permission(QueryModel, table=True):
    """A named, checkable capability (e.g. ``identity:write``)."""

    __tablename__ = "permissions"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    key: str = Field(index=True, unique=True)
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)


class RolePermission(QueryModel, table=True):
    """Join row granting a permission to a role."""

    __tablename__ = "role_permissions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_perm"),
    )

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    role_id: UUID = Field(foreign_key="roles.id", index=True)
    permission_id: UUID = Field(foreign_key="permissions.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)


class UserRole(QueryModel, table=True):
    """Join row assigning an instance role to a user (auditable)."""

    __tablename__ = "user_roles"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    role_id: UUID = Field(foreign_key="roles.id", index=True)
    granted_at: datetime = Field(default_factory=utcnow)
    granted_by_user_id: UUID | None = Field(default=None, foreign_key="users.id")


class ServiceIdentity(QueryModel, table=True):
    """A machine principal (adapter, worker, connector callback, …).

    Tokens use a public ``token_selector`` (indexed, O(1) lookup) plus a secret
    verifier whose PBKDF2 hash is stored in ``token_hash``. The plaintext token is
    shown once at issue/rotation and never stored (AGENTS.md I-15, `05-OPS` §3.4).
    """

    __tablename__ = "service_identities"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    name: str = Field(index=True, unique=True)
    audience: str = Field(default="")
    scopes: str = Field(default="")  # space-delimited scope tokens
    token_selector: str = Field(index=True, unique=True)
    token_hash: str = Field(default="")
    status: str = Field(default=IDENTITY_STATUS_ACTIVE, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: datetime | None = Field(default=None)
    rotated_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)

    @property
    def scope_set(self) -> frozenset[str]:
        """Return the parsed scope tokens."""
        return frozenset(s for s in self.scopes.split() if s)


class ChannelIdentity(QueryModel, table=True):
    """Maps a Hermes platform user/chat to an Ecom-OS user (`05-OPS` §3.3).

    An unmapped sender has no row and therefore no privileged identity (AGENTS.md
    I-09). The effective role is re-resolved at invocation time from the mapped user;
    ``role_snapshot`` is informational only.
    """

    __tablename__ = "channel_identities"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_account",
            "platform_user_id",
            name="uq_channel_identities_platform_user",
        ),
    )

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    platform: str = Field(index=True)
    platform_account: str = Field(default="")
    platform_user_id: str = Field(index=True)
    chat_id: str | None = Field(default=None)
    channel_id: str | None = Field(default=None)
    role_snapshot: str = Field(default="")
    status: str = Field(default=IDENTITY_STATUS_ACTIVE, index=True)
    hermes_profile_id: str | None = Field(default=None)
    verified_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)


class PlatformBootstrap(QueryModel, table=True):
    """Singleton owner-bootstrap gate (`05-OPS` §3.1).

    Open until the first owner is created, then closed; only a host recovery command
    re-opens it. The ``singleton`` unique flag guarantees a single row.
    """

    __tablename__ = "platform_bootstrap"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    singleton: bool = Field(default=True, unique=True)
    status: str = Field(default=BOOTSTRAP_OPEN)
    owner_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    opened_at: datetime = Field(default_factory=utcnow)
    closed_at: datetime | None = Field(default=None)
