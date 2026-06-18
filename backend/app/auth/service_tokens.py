"""Service-identity token issuance and verification.

A presented token is ``"<selector>.<verifier>"``:

* ``selector`` — a public random handle stored in plaintext and indexed, giving an
  O(1) lookup of the owning :class:`~app.models.identity.ServiceIdentity` (fixes the
  prototype's O(n) agent-token scan, RISKS A01-R07).
* ``verifier`` — the secret; only its PBKDF2 hash is stored (AGENTS.md I-15). The
  plaintext token is returned once at issue/rotation and never persisted.

PBKDF2 hashing reuses the vetted primitive in :mod:`app.core.agent_tokens`.
"""

from __future__ import annotations

import secrets
from typing import NamedTuple

from app.core.agent_tokens import hash_agent_token, verify_agent_token

__all__ = ["IssuedToken", "issue_token", "split_token", "hash_verifier", "verify_verifier"]

_SELECTOR_BYTES = 8
_VERIFIER_BYTES = 32
_SEPARATOR = "."


class IssuedToken(NamedTuple):
    """A freshly issued token: the plaintext (shown once) and its stored parts."""

    token: str  # full plaintext "<selector>.<verifier>" — return once, never store
    selector: str
    verifier_hash: str


def issue_token() -> IssuedToken:
    """Mint a new service token; persist only ``selector`` and ``verifier_hash``."""
    selector = secrets.token_urlsafe(_SELECTOR_BYTES)
    verifier = secrets.token_urlsafe(_VERIFIER_BYTES)
    token = f"{selector}{_SEPARATOR}{verifier}"
    return IssuedToken(token=token, selector=selector, verifier_hash=hash_agent_token(verifier))


def split_token(token: str) -> tuple[str, str] | None:
    """Split a presented token into ``(selector, verifier)`` or ``None`` if malformed."""
    if not token or _SEPARATOR not in token:
        return None
    selector, _, verifier = token.partition(_SEPARATOR)
    if not selector or not verifier:
        return None
    return selector, verifier


def hash_verifier(verifier: str) -> str:
    """Return the PBKDF2 hash representation of a verifier."""
    return hash_agent_token(verifier)


def verify_verifier(verifier: str, verifier_hash: str) -> bool:
    """Constant-time verify a verifier against its stored hash."""
    return verify_agent_token(verifier, verifier_hash)
