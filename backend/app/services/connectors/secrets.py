"""Secret handling for connector credentials.

Invariant 5: no secret is ever logged or returned in plaintext. We model secrets
with a wrapper whose repr/str/format never expose the underlying value — the value
is only obtainable through an explicit `.reveal()` call made at the HTTP boundary.

Invariant 1: the application persists only *connection references* (provider +
external account id / secret handle), never the raw credential. `resolve_secret`
maps a reference to its value from the server-side environment / secret store; the
value never round-trips through the database or API responses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

REDACTED = "***REDACTED***"


class Secret:
    """A credential value that refuses to reveal itself except via `.reveal()`.

    repr/str/format all return a redacted marker so the value cannot leak into
    logs, tracebacks, f-strings, or JSON by accident (Invariant 5).
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        """Return the raw value. Call ONLY at the point of use (e.g. an auth header)."""
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __len__(self) -> int:
        # Expose length (useful for validation) without exposing the value.
        return len(self._value)

    def __eq__(self, other: object) -> bool:
        # Constant-ish comparison; never compares by exposing the value externally.
        return isinstance(other, Secret) and other._value == self._value

    def __hash__(self) -> int:  # pragma: no cover - rarely used
        return hash(("Secret", len(self._value)))

    def __repr__(self) -> str:
        return f"Secret({REDACTED})"

    def __str__(self) -> str:
        return REDACTED

    def __format__(self, _spec: str) -> str:
        return REDACTED


class SecretResolutionError(RuntimeError):
    """Raised when a connection reference cannot be resolved to a secret."""


@dataclass(frozen=True)
class ConnectionRef:
    """What the database stores for a store/inbox connection — never the secret.

    - provider: "composio" | "direct"
    - external_id: Composio connected_account_id, or an env handle for direct mode.
    """

    provider: str
    external_id: str

    def __post_init__(self) -> None:
        if self.provider not in ("composio", "direct"):
            raise ValueError(f"unknown connection provider: {self.provider!r}")
        if not self.external_id:
            raise ValueError("connection reference requires an external_id")


def env_or_setting(name: str) -> str:
    """Read a config value by env-var NAME, falling back to pydantic Settings.

    The process environment wins (docker / shell / test monkeypatch); otherwise we
    consult Settings, which loads from `.env` in local runs. The name itself is not
    a secret, so this is safe.
    """
    raw = os.environ.get(name)
    if raw:
        return raw
    # Avoid a circular import at module load.
    from app.core.config import settings

    return str(getattr(settings, name.lower(), "") or "")


def resolve_secret(handle: str) -> Secret:
    """Resolve a credential handle (e.g. "SHOPIFY_ACCESS_TOKEN") to a Secret.

    The handle is a *name*, not the value — it is safe to store/log. The value is
    pulled from the environment / Settings at call time only, never persisted.
    """
    raw = env_or_setting(handle)
    if not raw:
        raise SecretResolutionError(
            f"no secret available for handle {handle!r}; connect the provider first",
        )
    return Secret(raw)
