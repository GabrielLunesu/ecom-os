"""Canonical money value type: integer minor units + ISO 4217 currency.

Normative basis: AGENTS.md I-16 / §6 ("Store money as integer minor units plus ISO
currency"), `03-ENGINEERING.md` §3 ("integer minor units plus ISO currency. Never
binary floating point"), Build Spec §10 ("calculations use integer minor units").

`Money` is immutable. Construction never accepts a binary ``float``; the only way to
build from a human-readable major amount is :meth:`from_major`, which routes through
:class:`decimal.Decimal` and rejects sub-minor-unit precision. Arithmetic across
currencies raises :class:`CurrencyMismatchError`.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Final

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["Money", "CurrencyMismatchError"]

# Minor-unit exponents for currencies whose default differs from 2. Storage is
# always (minor_units, currency); this map is only needed to render or parse a
# major amount. Unknown currencies default to 2, which is correct for the vast
# majority of ISO 4217 codes.
_MINOR_UNIT_EXPONENTS: Final[dict[str, int]] = {
    "JPY": 0,
    "KRW": 0,
    "VND": 0,
    "CLP": 0,
    "ISK": 0,
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
    "TND": 3,
}


class CurrencyMismatchError(ValueError):
    """Raised when an operation combines two different currencies."""


def minor_unit_exponent(currency: str) -> int:
    """Return the ISO 4217 minor-unit exponent for ``currency`` (default 2)."""
    return _MINOR_UNIT_EXPONENTS.get(currency.upper(), 2)


class Money(BaseModel):
    """An exact monetary amount stored as integer minor units + ISO currency."""

    model_config = ConfigDict(frozen=True)

    minor_units: int
    currency: str

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            msg = "currency must be a 3-letter ISO 4217 alphabetic code"
            raise ValueError(msg)
        return code

    @classmethod
    def zero(cls, currency: str) -> Money:
        """Return a zero amount in ``currency``."""
        return cls(minor_units=0, currency=currency)

    @classmethod
    def from_major(cls, amount: Decimal | int | str, currency: str) -> Money:
        """Build from a major amount (e.g. ``"19.99"`` USD → 1999 minor units).

        Accepts :class:`~decimal.Decimal`, ``int``, or ``str`` — never ``float``,
        because binary floats cannot represent decimal money exactly. A value with
        more precision than the currency's minor unit is rejected.
        """
        if isinstance(amount, float):  # pragma: no cover - defensive, typed out
            msg = "Money.from_major does not accept float; use Decimal or str"
            raise TypeError(msg)
        try:
            dec = Decimal(amount)
        except InvalidOperation as exc:
            msg = f"invalid decimal amount: {amount!r}"
            raise ValueError(msg) from exc
        exponent = minor_unit_exponent(currency)
        scaled = dec * (10**exponent)
        if scaled != scaled.to_integral_value():
            msg = f"amount {amount!r} has finer precision than {currency} minor unit"
            raise ValueError(msg)
        return cls(minor_units=int(scaled), currency=currency)

    def to_major(self) -> Decimal:
        """Return the exact major amount as a :class:`~decimal.Decimal`."""
        exponent = minor_unit_exponent(self.currency)
        return Decimal(self.minor_units) / Decimal(10**exponent)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            msg = f"cannot combine {self.currency} with {other.currency}"
            raise CurrencyMismatchError(msg)

    def add(self, other: Money) -> Money:
        """Return ``self + other``; both operands must share a currency."""
        self._require_same_currency(other)
        return Money(minor_units=self.minor_units + other.minor_units, currency=self.currency)

    def subtract(self, other: Money) -> Money:
        """Return ``self - other``; both operands must share a currency."""
        self._require_same_currency(other)
        return Money(minor_units=self.minor_units - other.minor_units, currency=self.currency)

    def __str__(self) -> str:
        return f"{self.to_major()} {self.currency}"
