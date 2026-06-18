"""Typed connector errors.

Every error is fail-closed and carries a stable ``code``, a ``retryable`` flag,
and an ``outcome_confidence`` so callers (and the durable action layer) can decide
whether a retry is safe. Messages are operator-facing and MUST NOT contain secrets
or raw provider payloads (Invariant I-15 / I-13).

Classification maps onto the action state machine (AGENTS.md §4, ADR-012):

- ``ConnectorBindingError`` — missing/ambiguous/wrong account; reject closed even in
  ``unrestricted`` mode (I-09, I-11). Never retried; never falls back to a default
  account.
- ``ConnectorTimeout`` — dispatch happened but the outcome cannot be proven; becomes
  ``outcome_unknown`` and MUST be reconciled before any dangerous retry (I-08).
- ``ConnectorUnavailable`` — the provider/account is unreachable; reads degrade to
  last-good (marked stale), writes stay queued.
- ``ConnectorRateLimited`` — provider-aware backoff (AGENTS.md §4).
"""

from __future__ import annotations

from typing import Literal

OutcomeConfidence = Literal["confirmed", "failed", "unknown"]


class ConnectorError(Exception):
    """Base class for all connector failures. Redacted, classified, fail-closed."""

    code: str = "connector_error"
    retryable: bool = False
    #: Confidence about whether an external side effect occurred.
    outcome_confidence: OutcomeConfidence = "failed"

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        # ``detail`` is an optional, already-redacted diagnostic string.
        self.detail = detail

    def to_dict(self) -> dict[str, object]:
        """A secret-free, serializable representation for traces/responses."""
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "outcome_confidence": self.outcome_confidence,
            "detail": self.detail,
        }


class ConnectorBindingError(ConnectorError):
    """Missing, ambiguous, or mismatched brand/store/connection/account binding.

    Raised when a write or read cannot be tied to exactly one connected account.
    This includes any attempt to use a "default"/"latest"/empty account. It is a
    technical-integrity rejection and applies in every autonomy mode (I-09, I-11).
    """

    code = "connector_binding_error"
    retryable = False
    outcome_confidence = "failed"


class CapabilityUnsupported(ConnectorError):
    """The (provider, capability, operation) tuple is not supported by any adapter."""

    code = "capability_unsupported"
    retryable = False
    outcome_confidence = "failed"


class ConnectorAuthError(ConnectorError):
    """Authentication/authorization against the exact account failed."""

    code = "connector_auth_error"
    retryable = False
    outcome_confidence = "failed"


class ConnectorRateLimited(ConnectorError):
    """Provider rate limit hit; retry after ``retry_after`` seconds with backoff."""

    code = "connector_rate_limited"
    retryable = True
    outcome_confidence = "failed"

    def __init__(
        self, message: str, *, retry_after: float | None = None, detail: str | None = None
    ) -> None:
        super().__init__(message, detail=detail)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data["retry_after"] = self.retry_after
        return data


class ConnectorUnavailable(ConnectorError):
    """Provider/account is unreachable (outage). Reads degrade to last-good."""

    code = "connector_unavailable"
    retryable = True
    outcome_confidence = "failed"


class ConnectorTimeout(ConnectorError):
    """Dispatch occurred but the outcome is unknown. Reconcile before retrying.

    This is the I-08 ``outcome_unknown`` carrier: a timeout/transport interruption
    after a request was sent is NOT automatically a failure.
    """

    code = "connector_timeout"
    retryable = False  # not safe to blindly retry; must reconcile first
    outcome_confidence = "unknown"


class WebhookVerificationError(ConnectorError):
    """A webhook failed raw-body signature/replay verification; never accepted."""

    code = "webhook_verification_error"
    retryable = False
    outcome_confidence = "failed"


class ProviderPayloadError(ConnectorError):
    """A provider payload could not be normalized into the domain contract.

    Raised by normalizers so raw provider shapes never leak past the connector
    boundary (AGENTS.md §10: database models are not serialized to external
    contracts; connector payloads stay evidence).
    """

    code = "provider_payload_error"
    retryable = False
    outcome_confidence = "failed"
