"""Globally-unique, time-sortable identifiers (UUIDv7).

Normative basis: AGENTS.md §6 ("Use globally unique sortable IDs") and
`04-DATA-AND-TRACEABILITY.md` §3 ("Ecom-OS generates UUIDv7 identifiers for new
internal records where supported. IDs are opaque to clients").

The Python standard library does not yet expose `uuid.uuid7` on the supported
runtime, so this module implements RFC 9562 §5.7 directly. New A01-owned tables
(roles, permissions, service/channel identities, …) use :func:`uuid7` as their
primary-key default. Existing prototype tables keep their `uuid4` defaults — we do
not retrofit every model (no big-bang rewrite); they remain globally unique, only
not time-sortable.
"""

from __future__ import annotations

import os
import time
from uuid import UUID

__all__ = ["uuid7", "Uuid7"]

# A UUIDv7 value is a normal :class:`uuid.UUID`; this alias documents intent at
# call sites and in type signatures (e.g. service-identity ids).
Uuid7 = UUID

_TS_MASK = (1 << 48) - 1
_RAND_A_MASK = (1 << 12) - 1
_RAND_B_MASK = (1 << 62) - 1


def uuid7() -> UUID:
    """Return a new time-ordered UUIDv7.

    Layout (most-significant bit first, RFC 9562 §5.7):
    48-bit Unix epoch milliseconds | 4-bit version (0b0111) | 12-bit random |
    2-bit variant (0b10) | 62-bit random. Values created in ascending wall-clock
    time sort ascending lexicographically and by integer value, which keeps
    database indexes append-friendly.
    """
    unix_ms = (time.time_ns() // 1_000_000) & _TS_MASK
    rand_a = int.from_bytes(os.urandom(2), "big") & _RAND_A_MASK
    rand_b = int.from_bytes(os.urandom(8), "big") & _RAND_B_MASK

    value = unix_ms << 80
    value |= 0x7 << 76  # version 7
    value |= rand_a << 64
    value |= 0x2 << 62  # RFC 4122 variant (0b10)
    value |= rand_b
    return UUID(int=value)
