"""Secret redaction at serialization boundaries.

Normative basis: AGENTS.md I-15 (secrets never become ordinary data),
`05-OPERATIONS-AND-SECURITY.md` §4.2 ("redaction at structured-logging boundaries, not
ad hoc post-serialization string replacement"), and §12.2 invariant ("no secret appears
in logs, traces, API responses, or tool output") backed by a secret-detection corpus.

Two complementary mechanisms:

* :func:`redact_mapping` / :func:`redact_value` — key-aware redaction applied at the
  structured-logging formatter and the typed-error ``details`` boundary. Any field whose
  key looks secret-bearing (token, password, authorization, …) is replaced.
* :func:`scan_for_secrets` — value-pattern detection (Shopify/OpenAI/Anthropic keys,
  bearer tokens, PBKDF2 hashes) used by the CI corpus test to catch leaks that slip
  through key-based redaction.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = [
    "REDACTED",
    "is_sensitive_key",
    "redact_value",
    "redact_mapping",
    "scan_for_secrets",
]

REDACTED = "***redacted***"

# Substrings that mark a mapping key as secret-bearing (case-insensitive).
_SENSITIVE_KEY_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
    "credential",
    "private_key",
    "verifier",
    "signature",
    "bearer",
    "access_key",
    "session_key",
)

# Keys that contain a sensitive substring but are safe (non-secret identifiers).
_SAFE_KEY_ALLOWLIST: frozenset[str] = frozenset(
    {
        "token_selector",  # public selector, not a secret
        "token_prefix",
        "tokens",  # e.g. token counts
        "token_count",
        "tokens_used",
        "request_id",
        "trace_id",
    },
)

# Value patterns that are secrets regardless of their key.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"shp(at|ss|ca|pa)_[A-Za-z0-9]{16,}"),  # Shopify tokens
    re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),  # Anthropic keys
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE),  # bearer tokens
    re.compile(r"pbkdf2_sha256\$\d+\$[A-Za-z0-9_-]+\$[A-Za-z0-9_-]+"),  # password hashes
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key ids
)


def is_sensitive_key(key: str) -> bool:
    """Return whether a mapping key denotes a secret-bearing value."""
    lowered = key.lower()
    if lowered in _SAFE_KEY_ALLOWLIST:
        return False
    return any(token in lowered for token in _SENSITIVE_KEY_SUBSTRINGS)


def redact_value(key: str, value: Any) -> Any:
    """Redact ``value`` if ``key`` is sensitive; recurse into nested mappings/lists."""
    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, (list, tuple)):
        return [redact_value(key, item) for item in value]
    return value


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``data`` with secret-bearing values redacted."""
    return {key: redact_value(str(key), value) for key, value in data.items()}


def scan_for_secrets(text: str) -> list[str]:
    """Return every secret-looking substring found in ``text`` (for the CI corpus)."""
    findings: list[str] = []
    for pattern in _SECRET_PATTERNS:
        findings.extend(match.group(0) for match in pattern.finditer(text))
    return findings
