"""A01 foundation: identity migration applies/restarts on seeded prototype data.

Hermetic: a temp sqlite file stands in for the deployment DB. We materialise the
pre-A01 prototype schema (everything except the new identity tables), seed realistic
prototype rows (user/brand/store), then run the real Alembic migration
``a01_0001_identity`` and verify it creates the identity tables without disturbing the
seeded data, is safe to re-run (restart), and is reversible.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlmodel import Session, SQLModel

import app.models  # noqa: F401 - register metadata
from app.core.config import settings
from app.models.brand import Brand, Store
from app.models.users import User

BACKEND_ROOT = Path(__file__).resolve().parents[1]

_IDENTITY_TABLES = {
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "service_identities",
    "channel_identities",
    "platform_bootstrap",
}
_PRE_A01_HEAD = "a0b1c2d3e4f5"


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    return cfg


def _seed_prototype(engine: sa.Engine) -> dict[str, str]:
    # Create every prototype table EXCEPT the identity tables (pre-migration state).
    pre_tables = [
        table for name, table in SQLModel.metadata.tables.items() if name not in _IDENTITY_TABLES
    ]
    SQLModel.metadata.create_all(engine, tables=pre_tables)
    with Session(engine) as session:
        user = User(clerk_user_id="proto-user", email="owner@example.com", name="Proto Owner")
        brand = Brand(name="Proto Brand")
        session.add(user)
        session.add(brand)
        session.commit()
        session.refresh(user)
        session.refresh(brand)
        store = Store(
            brand_id=brand.id,
            name="Proto Store",
            domain="proto-shop.myshopify.com",
            provider="direct",
            external_id="proto-shop",
            status="active",
        )
        session.add(store)
        session.commit()
        return {"user_id": str(user.id), "brand_id": str(brand.id)}


@pytest.fixture
def sqlite_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sa.Engine:
    db_path = tmp_path / "proto.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)
    return sa.create_engine(url)


def _tables(engine: sa.Engine) -> set[str]:
    return set(sa.inspect(engine).get_table_names())


class TestIdentityMigration:
    def test_upgrade_creates_identity_tables_preserving_data(self, sqlite_db: sa.Engine) -> None:
        seeded = _seed_prototype(sqlite_db)
        assert not (_IDENTITY_TABLES & _tables(sqlite_db))  # absent pre-migration

        cfg = _alembic_config()
        command.stamp(cfg, _PRE_A01_HEAD)
        command.upgrade(cfg, "head")

        tables = _tables(sqlite_db)
        assert _IDENTITY_TABLES <= tables
        # Seeded prototype rows survive the migration untouched.
        with sqlite_db.connect() as conn:
            users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
            stores = conn.execute(sa.text("SELECT name FROM stores")).fetchall()
        # sqlite stores sa.Uuid() as dash-less hex; compare canonical UUID values.
        assert [str(UUID(r[0])) for r in users] == [seeded["user_id"]]
        assert [r[0] for r in stores] == ["Proto Store"]

    def test_restart_is_idempotent(self, sqlite_db: sa.Engine) -> None:
        _seed_prototype(sqlite_db)
        cfg = _alembic_config()
        command.stamp(cfg, _PRE_A01_HEAD)
        command.upgrade(cfg, "head")
        # Simulate a process restart re-running startup migrations: must not error.
        command.upgrade(cfg, "head")
        assert _IDENTITY_TABLES <= _tables(sqlite_db)

    def test_downgrade_removes_identity_tables_only(self, sqlite_db: sa.Engine) -> None:
        _seed_prototype(sqlite_db)
        cfg = _alembic_config()
        command.stamp(cfg, _PRE_A01_HEAD)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, _PRE_A01_HEAD)

        tables = _tables(sqlite_db)
        assert not (_IDENTITY_TABLES & tables)
        assert "users" in tables and "stores" in tables  # prototype intact
