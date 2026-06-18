"""Versioned, typed API error envelope.

Normative basis: `03-ENGINEERING.md` §10 ("Error model"). Every expected error has a
stable machine code, a human-readable message, a retry classification, a trace id,
safe details, and optional remediation. The fifteen :class:`ErrorCode` members are the
exact normative minimum.

Wire shape (backward compatible with the prototype's ``{detail, request_id}`` and the
``LLMErrorResponse`` documented contract — ``detail`` remains a human string):

    {
      "detail":      "<human message>",
      "code":        "<ErrorCode>",
      "retryable":   <bool>,
      "trace_id":    "<str|null>",
      "request_id":  "<str|null>",
      "remediation": "<str|null>",      # omitted when null
      "details":     { ... } | null     # omitted when null; MUST be secret-free
    }

Raise :class:`ApiError` from application/domain code; the handler installed by
``app.core.error_handling`` serializes it. Do not put secrets in ``details`` — that is
caller-supplied and is returned to clients (AGENTS.md I-15).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import status
from pydantic import BaseModel, Field

__all__ = ["ErrorCode", "ErrorEnvelope", "ApiError"]


class ErrorCode(str, Enum):
    """Stable machine-readable error codes (`03-ENGINEERING.md` §10)."""

    VALIDATION_ERROR = "validation_error"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    GRANT_DISABLED = "grant_disabled"
    APPROVAL_REQUIRED = "approval_required"
    POLICY_REJECTED = "policy_rejected"
    RESOURCE_CONFLICT = "resource_conflict"
    STALE_STATE = "stale_state"
    CONNECTOR_UNAVAILABLE = "connector_unavailable"
    RATE_LIMITED = "rate_limited"
    OUTCOME_UNKNOWN = "outcome_unknown"
    HERMES_UNAVAILABLE = "hermes_unavailable"
    HERMES_INCOMPATIBLE = "hermes_incompatible"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL_ERROR = "internal_error"


# Default HTTP status for each code. Callers may override per raise.
_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.GRANT_DISABLED: status.HTTP_403_FORBIDDEN,
    ErrorCode.APPROVAL_REQUIRED: status.HTTP_409_CONFLICT,
    ErrorCode.POLICY_REJECTED: status.HTTP_403_FORBIDDEN,
    ErrorCode.RESOURCE_CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.STALE_STATE: status.HTTP_409_CONFLICT,
    ErrorCode.CONNECTOR_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.OUTCOME_UNKNOWN: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.HERMES_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.HERMES_INCOMPATIBLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.DEPENDENCY_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# Default retry classification. `outcome_unknown` is deliberately NOT retryable
# (AGENTS.md I-08: do not blindly retry an ambiguous outcome).
_RETRYABLE: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.RATE_LIMITED,
        ErrorCode.CONNECTOR_UNAVAILABLE,
        ErrorCode.HERMES_UNAVAILABLE,
        ErrorCode.DEPENDENCY_UNAVAILABLE,
    },
)


def default_http_status(code: ErrorCode) -> int:
    """Return the default HTTP status for ``code``."""
    return _HTTP_STATUS[code]


def default_retryable(code: ErrorCode) -> bool:
    """Return the default retry classification for ``code``."""
    return code in _RETRYABLE


class ErrorEnvelope(BaseModel):
    """Serialized error contract returned to clients and generated to TS."""

    detail: str = Field(description="Human-readable message; safe to display.")
    code: ErrorCode = Field(description="Stable machine-readable error code.")
    retryable: bool = Field(description="Whether the client may safely retry.")
    trace_id: str | None = Field(default=None, description="Trace correlation id.")
    request_id: str | None = Field(default=None, description="Request correlation id.")
    remediation: str | None = Field(
        default=None,
        description="Optional next step the caller can take to resolve the error.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional safe, secret-free structured context.",
    )


class ApiError(Exception):
    """Typed application error that serializes to :class:`ErrorEnvelope`.

    Example::

        raise ApiError(ErrorCode.FORBIDDEN, "You may not edit this store.")
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        http_status: int | None = None,
        retryable: bool | None = None,
        remediation: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Create a typed error; status/retryable default from ``code``."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status if http_status is not None else default_http_status(code)
        self.retryable = retryable if retryable is not None else default_retryable(code)
        self.remediation = remediation
        self.details = details
        self.headers = headers

    def to_envelope(
        self,
        *,
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> ErrorEnvelope:
        """Build the serializable envelope, attaching correlation ids."""
        return ErrorEnvelope(
            detail=self.message,
            code=self.code,
            retryable=self.retryable,
            trace_id=trace_id,
            request_id=request_id,
            remediation=self.remediation,
            details=self.details,
        )
