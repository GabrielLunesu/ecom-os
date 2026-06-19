"""Verify Alembic upgrade-to-head against a disposable PostgreSQL database.

Set A02_POSTGRES_TEST_DATABASE_URL to an empty disposable PostgreSQL database.
The script refuses to run against a database that already has user tables.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from alembic import command
from alembic.config import Config

REQUIRED_TABLES = {
    "durable_inbox_events",
    "durable_outbox_events",
    "durable_jobs",
    "traces",
    "runs",
    "spans",
    "tool_invocations",
    "evidence",
    "evidence_links",
    "audit_records",
    "incidents",
    "actions",
    "action_attempts",
    "action_state_history",
}


def _sync_psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _assert_postgres(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg", "postgres"}:
        msg = "A02_POSTGRES_TEST_DATABASE_URL must point to PostgreSQL"
        raise SystemExit(msg)


def _current_tables(url: str) -> set[str]:
    with psycopg.connect(_sync_psycopg_url(url)) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select tablename
                from pg_tables
                where schemaname = 'public'
                """)
            return {str(row[0]) for row in cur.fetchall()}


def _current_revision(url: str) -> str:
    with psycopg.connect(_sync_psycopg_url(url)) as conn:
        with conn.cursor() as cur:
            cur.execute("select version_num from alembic_version")
            row = cur.fetchone()
            return str(row[0]) if row else ""


def _alembic_config(root: Path, database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(root / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    return cfg


def main() -> int:
    database_url = os.environ.get("A02_POSTGRES_TEST_DATABASE_URL", "").strip()
    if not database_url:
        print("SKIP: set A02_POSTGRES_TEST_DATABASE_URL to an empty disposable PostgreSQL DB")
        return 77
    _assert_postgres(database_url)
    existing = _current_tables(database_url)
    if existing:
        print("ERROR: test database is not empty; refusing to run destructive migration check")
        print("Existing tables: " + ", ".join(sorted(existing)))
        return 2

    root = Path(__file__).resolve().parents[1]
    command.upgrade(_alembic_config(root, database_url), "head")

    tables = _current_tables(database_url)
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        print("ERROR: durable core tables missing after upgrade: " + ", ".join(missing))
        return 1

    revision = _current_revision(database_url)
    print("OK: PostgreSQL migration upgrade reached head")
    print(f"Revision: {revision}")
    print(f"Durable tables verified: {len(REQUIRED_TABLES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
