"""A01 foundation: common types (UUIDv7, Money, time) and typed errors."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.errors import ApiError, ErrorCode, ErrorEnvelope
from app.core.ids import uuid7
from app.core.money import CurrencyMismatchError, Money
from app.core.time import ensure_utc, now_utc, to_timezone, utcnow


class TestUuid7:
    def test_version_and_variant(self) -> None:
        value = uuid7()
        assert value.version == 7
        # RFC 4122 variant => two most-significant bits of clock_seq_hi are 0b10.
        assert (value.int >> 62) & 0b11 == 0b10

    def test_unique(self) -> None:
        values = {uuid7() for _ in range(1000)}
        assert len(values) == 1000

    def test_time_sortable(self) -> None:
        # IDs minted later must sort after earlier ones (ms-resolution prefix).
        first = uuid7()
        import time

        time.sleep(0.005)
        second = uuid7()
        assert first < second
        assert str(first) < str(second)


class TestMoney:
    def test_from_major_usd(self) -> None:
        assert Money.from_major("19.99", "USD").minor_units == 1999

    def test_zero_decimal_currency(self) -> None:
        assert Money.from_major("500", "JPY").minor_units == 500

    def test_three_decimal_currency(self) -> None:
        assert Money.from_major("1.234", "BHD").minor_units == 1234

    def test_rejects_float(self) -> None:
        with pytest.raises(TypeError):
            Money.from_major(19.99, "USD")  # type: ignore[arg-type]

    def test_rejects_subminor_precision(self) -> None:
        with pytest.raises(ValueError, match="finer precision"):
            Money.from_major("1.001", "USD")

    def test_currency_normalized_and_validated(self) -> None:
        assert Money(minor_units=100, currency="usd").currency == "USD"
        with pytest.raises(ValueError, match="ISO 4217"):
            Money(minor_units=100, currency="US")

    def test_arithmetic_same_currency(self) -> None:
        total = Money(minor_units=100, currency="USD").add(Money(minor_units=50, currency="USD"))
        assert total.minor_units == 150

    def test_arithmetic_currency_mismatch(self) -> None:
        with pytest.raises(CurrencyMismatchError):
            Money(minor_units=100, currency="USD").add(Money(minor_units=50, currency="EUR"))

    def test_immutable(self) -> None:
        money = Money(minor_units=100, currency="USD")
        with pytest.raises(Exception):  # noqa: B017,PT011 - pydantic frozen error
            money.minor_units = 200  # type: ignore[misc]

    def test_to_major_roundtrip(self) -> None:
        assert Money.from_major("19.99", "USD").to_major() == Decimal("19.99")


class TestTime:
    def test_utcnow_is_naive(self) -> None:
        assert utcnow().tzinfo is None

    def test_now_utc_is_aware(self) -> None:
        assert now_utc().tzinfo is UTC

    def test_ensure_utc_naive_treated_as_utc(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0, 0)  # noqa: DTZ001 - intentional naive
        assert ensure_utc(naive).tzinfo is UTC

    def test_to_timezone(self) -> None:
        aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        ny = to_timezone(aware, "America/New_York")
        assert ny.hour == 7  # noqa: PLR2004 - EST offset

    def test_to_timezone_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="unknown IANA timezone"):
            to_timezone(now_utc(), "Not/AZone")


class TestErrors:
    def test_all_fifteen_codes_present(self) -> None:
        expected = {
            "validation_error",
            "unauthenticated",
            "forbidden",
            "grant_disabled",
            "approval_required",
            "policy_rejected",
            "resource_conflict",
            "stale_state",
            "connector_unavailable",
            "rate_limited",
            "outcome_unknown",
            "hermes_unavailable",
            "hermes_incompatible",
            "dependency_unavailable",
            "internal_error",
        }
        assert {c.value for c in ErrorCode} == expected

    def test_default_status_mapping(self) -> None:
        assert ApiError(ErrorCode.UNAUTHENTICATED, "x").http_status == 401
        assert ApiError(ErrorCode.FORBIDDEN, "x").http_status == 403
        assert ApiError(ErrorCode.RATE_LIMITED, "x").http_status == 429
        assert ApiError(ErrorCode.INTERNAL_ERROR, "x").http_status == 500

    def test_outcome_unknown_not_retryable(self) -> None:
        # AGENTS.md I-08: never blindly retry an ambiguous outcome.
        assert ApiError(ErrorCode.OUTCOME_UNKNOWN, "x").retryable is False

    def test_transient_codes_retryable(self) -> None:
        assert ApiError(ErrorCode.RATE_LIMITED, "x").retryable is True
        assert ApiError(ErrorCode.CONNECTOR_UNAVAILABLE, "x").retryable is True

    def test_envelope_shape(self) -> None:
        err = ApiError(
            ErrorCode.FORBIDDEN,
            "nope",
            remediation="ask an admin",
            details={"store_id": "abc"},
        )
        env = err.to_envelope(trace_id="t1", request_id="r1")
        assert isinstance(env, ErrorEnvelope)
        dumped = env.model_dump(exclude_none=True)
        assert dumped == {
            "detail": "nope",
            "code": "forbidden",
            "retryable": False,
            "trace_id": "t1",
            "request_id": "r1",
            "remediation": "ask an admin",
            "details": {"store_id": "abc"},
        }
