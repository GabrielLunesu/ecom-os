"""Generic action intent, attempt, and reconciliation primitives."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.models.actions import Action, ActionAttempt, ActionStateHistory

TERMINAL_SUCCESS_STATES = {"succeeded", "reconciled_succeeded"}
UNKNOWN_STATES = {"outcome_unknown"}
SECRET_FIELD_KEYS = {
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


class ActionValidationError(ValueError):
    """Raised when an action is missing technical-integrity fields."""


class ActionIntentConflictError(RuntimeError):
    """Raised when the same intent key points at different frozen arguments."""


class OutcomeUnknownRetryBlockedError(RuntimeError):
    """Raised when a dangerous retry is attempted before reconciliation."""


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def action_digest(
    *,
    action_type: str,
    schema_version: int,
    store_id: UUID,
    connection_id: UUID,
    target_type: str,
    target_id: str,
    normalized_arguments: dict[str, Any],
) -> str:
    payload = {
        "action_type": action_type,
        "schema_version": schema_version,
        "store_id": str(store_id),
        "connection_id": str(connection_id),
        "target_type": target_type,
        "target_id": target_id,
        "normalized_arguments": normalized_arguments,
    }
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def request_fingerprint(value: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _contains_secret_field_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().lower() in SECRET_FIELD_KEYS:
                return True
            if _contains_secret_field_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_field_key(item) for item in value)
    return False


async def _append_history(
    session: AsyncSession,
    action: Action,
    *,
    to_state: str,
    reason: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ActionStateHistory:
    history = ActionStateHistory(
        action_id=action.id,
        from_state=action.state,
        to_state=to_state,
        reason=reason,
        actor_type=actor_type,
        actor_id=actor_id,
        transition_metadata=metadata or {},
    )
    action.state = to_state
    action.updated_at = utcnow()
    if to_state in TERMINAL_SUCCESS_STATES or to_state in {
        "failed_permanent",
        "cancelled",
    }:
        action.completed_at = action.updated_at
    session.add(action)
    session.add(history)
    await session.flush()
    return history


async def create_or_reuse_action(
    session: AsyncSession,
    *,
    trace_id: UUID,
    action_type: str,
    schema_version: int,
    store_id: UUID | None,
    connection_id: UUID | None,
    target_type: str,
    target_id: str,
    normalized_arguments: dict[str, Any],
    requested_actor_type: str,
    requested_actor_id: str,
    autonomy_mode: str,
    intent_key: str,
    tool_invocation_id: UUID | None = None,
    requested_run_id: UUID | None = None,
    requested_session_id: str | None = None,
    effective_grant: dict[str, Any] | None = None,
    policy_version: str | None = None,
    policy_result: dict[str, Any] | None = None,
    approval_required: bool = False,
    approval_id: UUID | None = None,
    initial_state: str = "proposed",
) -> tuple[Action, bool]:
    """Freeze or reuse one normalized external-write action intent."""

    if store_id is None or connection_id is None:
        raise ActionValidationError("external actions require exact store_id and connection_id")
    if not requested_actor_type or not requested_actor_id:
        raise ActionValidationError("external actions require an exact requested actor")
    if not intent_key:
        raise ActionValidationError("external actions require an intent_key")
    if _contains_secret_field_key(normalized_arguments):
        raise ActionValidationError("external action arguments must be redacted before recording")
    if _contains_secret_field_key(effective_grant):
        raise ActionValidationError("external action grant data must be redacted before recording")
    if _contains_secret_field_key(policy_result):
        raise ActionValidationError(
            "external action policy result must be redacted before recording"
        )

    digest = action_digest(
        action_type=action_type,
        schema_version=schema_version,
        store_id=store_id,
        connection_id=connection_id,
        target_type=target_type,
        target_id=target_id,
        normalized_arguments=normalized_arguments,
    )
    existing = (
        await session.exec(
            select(Action)
            .where(Action.store_id == store_id)
            .where(Action.connection_id == connection_id)
            .where(Action.action_type == action_type)
            .where(Action.intent_key == intent_key)
        )
    ).first()
    if existing is not None:
        if existing.action_digest != digest:
            raise ActionIntentConflictError("intent key already exists with a different digest")
        return existing, False

    action = Action(
        trace_id=trace_id,
        tool_invocation_id=tool_invocation_id,
        action_type=action_type,
        schema_version=schema_version,
        store_id=store_id,
        connection_id=connection_id,
        target_type=target_type,
        target_id=target_id,
        normalized_arguments=normalized_arguments,
        action_digest=digest,
        requested_actor_type=requested_actor_type,
        requested_actor_id=requested_actor_id,
        requested_run_id=requested_run_id,
        requested_session_id=requested_session_id,
        effective_grant=effective_grant or {},
        autonomy_mode=autonomy_mode,
        policy_version=policy_version,
        policy_result=policy_result,
        approval_required=approval_required,
        approval_id=approval_id,
        intent_key=intent_key,
        state=initial_state,
    )
    session.add(action)
    await session.flush()
    history = ActionStateHistory(action_id=action.id, from_state=None, to_state=initial_state)
    session.add(history)
    await session.flush()
    return action, True


async def start_attempt(
    session: AsyncSession,
    action: Action,
    *,
    connector: str,
    provider_idempotency_key: str,
    safe_request_summary: dict[str, Any],
    allow_after_unknown: bool = False,
) -> ActionAttempt:
    """Create an action attempt and move the action to `executing`."""

    if action.state in UNKNOWN_STATES and not allow_after_unknown:
        raise OutcomeUnknownRetryBlockedError(
            "action outcome is unknown; reconcile or manually resolve before retry"
        )
    if _contains_secret_field_key(safe_request_summary):
        raise ActionValidationError(
            "action attempt request summary must be redacted before recording"
        )
    max_attempt = (
        await session.exec(
            select(func.max(ActionAttempt.attempt_number)).where(
                ActionAttempt.action_id == action.id
            )
        )
    ).one()
    attempt_number = int(max_attempt or 0) + 1
    attempt = ActionAttempt(
        action_id=action.id,
        attempt_number=attempt_number,
        connector=connector,
        connection_id=action.connection_id,
        provider_idempotency_key=provider_idempotency_key,
        request_fingerprint=request_fingerprint(safe_request_summary),
        safe_request_summary=safe_request_summary,
    )
    session.add(attempt)
    await _append_history(session, action, to_state="executing", reason="attempt_started")
    await session.flush()
    return attempt


async def finish_attempt(
    session: AsyncSession,
    action: Action,
    attempt: ActionAttempt,
    *,
    outcome_state: str,
    http_status_category: str | None = None,
    safe_response_summary: dict[str, Any] | None = None,
    provider_request_id: str | None = None,
    provider_operation_id: str | None = None,
    retry_classification: str | None = None,
    outcome_confidence: str = "unknown",
    error_reference: str | None = None,
    reconciliation_due_at: datetime | None = None,
) -> ActionAttempt:
    """Record provider outcome and transition the action."""

    if outcome_state not in {
        "succeeded",
        "failed_retryable",
        "failed_permanent",
        "outcome_unknown",
        "reconciled_succeeded",
        "reconciled_failed",
        "manual_resolution",
    }:
        raise ValueError(f"unsupported action outcome_state={outcome_state!r}")
    if _contains_secret_field_key(safe_response_summary):
        raise ActionValidationError(
            "action attempt response summary must be redacted before recording"
        )
    attempt.http_status_category = http_status_category
    attempt.safe_response_summary = safe_response_summary
    attempt.provider_request_id = provider_request_id
    attempt.provider_operation_id = provider_operation_id
    attempt.retry_classification = retry_classification
    attempt.outcome_confidence = outcome_confidence
    attempt.error_reference = error_reference
    attempt.reconciliation_due_at = reconciliation_due_at
    attempt.ended_at = utcnow()
    session.add(attempt)
    action.final_outcome_summary = safe_response_summary or {"outcome_state": outcome_state}
    await _append_history(
        session,
        action,
        to_state=outcome_state,
        reason="attempt_finished",
        metadata={
            "attempt_id": str(attempt.id),
            "outcome_confidence": outcome_confidence,
            "retry_classification": retry_classification,
        },
    )
    await session.flush()
    return attempt


async def reconcile_unknown_action(
    session: AsyncSession,
    action: Action,
    *,
    reconciled_state: str,
    evidence: dict[str, Any],
    actor_type: str = "system",
    actor_id: str = "reconciliation",
) -> Action:
    """Resolve an `outcome_unknown` action from provider/manual evidence."""

    if action.state != "outcome_unknown":
        raise ValueError("only outcome_unknown actions can be reconciled by this helper")
    if _contains_secret_field_key(evidence):
        raise ActionValidationError(
            "action reconciliation evidence must be redacted before recording"
        )
    if reconciled_state not in {
        "reconciled_succeeded",
        "reconciled_failed",
        "manual_resolution",
    }:
        raise ValueError(f"unsupported reconciled_state={reconciled_state!r}")
    action.final_outcome_summary = evidence
    await _append_history(
        session,
        action,
        to_state=reconciled_state,
        reason="reconciliation",
        actor_type=actor_type,
        actor_id=actor_id,
        metadata=evidence,
    )
    await session.flush()
    return action


async def search_actions(
    session: AsyncSession,
    *,
    trace_id: UUID | None = None,
    state: str | None = None,
    action_type: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> list[Action]:
    """List durable action intents with operational filters."""

    statement = select(Action).order_by(col(Action.created_at).desc())
    if trace_id is not None:
        statement = statement.where(Action.trace_id == trace_id)
    if state:
        statement = statement.where(Action.state == state)
    if action_type:
        statement = statement.where(Action.action_type == action_type)
    if target_type:
        statement = statement.where(Action.target_type == target_type)
    if target_id:
        statement = statement.where(Action.target_id == target_id)
    return list((await session.exec(statement)).all())
