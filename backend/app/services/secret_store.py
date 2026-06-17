"""Dashboard-managed encrypted secret store (Invariants 1 & 5).

Secrets the operator sets from Settings are encrypted at rest with Fernet and held
in a small in-process cache for the connector layer to resolve. The plaintext value
is NEVER logged, serialized, or returned by these functions — only handles are.

The Fernet key is *derived* deterministically from an existing config value, so the
store needs no extra configuration: we hash SECRETS_KEY (or fall back to the always-
present LOCAL_AUTH_TOKEN) into a stable 32-byte key.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.brand import Brand
from app.models.secret_entry import SecretEntry
from app.services.connectors.secrets import env_or_setting

# Decrypted handle -> value. Populated by load_secret_cache and kept in sync by
# set_secret / unset_secret. Never logged.
_CACHE: dict[str, str] = {}


def _fernet() -> Fernet:
    """Derive the Fernet key deterministically from existing config."""
    seed = env_or_setting("SECRETS_KEY") or env_or_setting("LOCAL_AUTH_TOKEN")
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
    return Fernet(key)


async def set_secret(session: AsyncSession, brand: Brand, handle: str, value: str) -> None:
    """Encrypt and upsert a secret, then refresh the in-process cache."""
    ciphertext = _fernet().encrypt(value.encode()).decode()
    existing = (
        await session.exec(select(SecretEntry).where(SecretEntry.handle == handle))
    ).first()
    if existing is None:
        session.add(
            SecretEntry(brand_id=brand.id, handle=handle, ciphertext=ciphertext)
        )
    else:
        existing.ciphertext = ciphertext
        existing.updated_at = utcnow()
        session.add(existing)
    await session.commit()
    _CACHE[handle] = value


async def unset_secret(session: AsyncSession, brand: Brand, handle: str) -> None:
    """Delete a secret and drop it from the cache."""
    existing = (
        await session.exec(select(SecretEntry).where(SecretEntry.handle == handle))
    ).first()
    if existing is not None:
        await session.delete(existing)
        await session.commit()
    _CACHE.pop(handle, None)


async def list_handles(session: AsyncSession) -> list[str]:
    """Return the handles that are set — NEVER the values."""
    rows = (await session.exec(select(SecretEntry).order_by(SecretEntry.handle))).all()
    return [r.handle for r in rows]


async def load_secret_cache(session: AsyncSession) -> None:
    """Decrypt all stored secrets into the module cache (call once at startup)."""
    fernet = _fernet()
    rows = (await session.exec(select(SecretEntry))).all()
    _CACHE.clear()
    for row in rows:
        _CACHE[row.handle] = fernet.decrypt(row.ciphertext.encode()).decode()


def get_cached(handle: str) -> str | None:
    """Return the decrypted value for a handle, or None if unset."""
    return _CACHE.get(handle)
