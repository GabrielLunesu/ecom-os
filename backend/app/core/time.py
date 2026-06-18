"""Time-related helpers shared across backend modules.

Normative basis: AGENTS.md §6 ("Store timestamps in UTC; reports show the effective
timezone") and `03-ENGINEERING.md` §3 ("UTC in storage; IANA timezone at presentation
and reporting boundaries").

Two layers exist intentionally:

* :func:`utcnow` returns a **naive** UTC datetime. It is the legacy default used by
  every existing prototype model/column and is kept for schema/query compatibility;
  do not change its return type without migrating those columns (RISKS A01-R03).
* :func:`now_utc`, :func:`ensure_utc`, and :func:`to_timezone` are the tz-aware v2
  helpers. New code that crosses presentation/reporting boundaries should use them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = ["utcnow", "now_utc", "ensure_utc", "to_timezone"]


def utcnow() -> datetime:
    """Return a naive UTC datetime (legacy; matches existing DB columns)."""
    # Keep naive UTC values for compatibility with existing DB schema/queries.
    return datetime.now(UTC).replace(tzinfo=None)


def now_utc() -> datetime:
    """Return a timezone-aware UTC datetime (v2 default for new code)."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as a tz-aware UTC datetime.

    Naive inputs are interpreted as UTC (the storage convention); aware inputs are
    converted to UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_timezone(value: datetime, tz_name: str) -> datetime:
    """Convert ``value`` to the IANA timezone ``tz_name`` for presentation."""
    try:
        target = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        msg = f"unknown IANA timezone: {tz_name!r}"
        raise ValueError(msg) from exc
    return ensure_utc(value).astimezone(target)
