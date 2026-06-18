"""Durable external-write path: action intent, attempts, and reconciliation.

This is the A04-side consumer of the A02 durable action port (locally stood-in by
:class:`LocalDurableActionStore`). It enforces the write invariants:

- **I-06** every external write is one normalized, durable action with ≥1 attempt;
- **I-07** a unique idempotency intent key makes retries/duplicates change state once;
- **I-08** a post-dispatch timeout becomes ``outcome_unknown`` and is NOT retried
  until reconciliation resolves it.

No connector adapter performs a hidden write outside this contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connectors.binding import ConnectionBinding
from app.connectors.errors import ConnectorError, ConnectorTimeout
from app.connectors.models import CommerceAction, CommerceActionAttempt
from app.connectors.ports import ConnectorPort, ProviderCommand, payload_hash
from app.core.time import utcnow

# Terminal success states: a duplicate intent must not re-dispatch.
_SUCCESS_STATES = frozenset({"succeeded", "reconciled_succeeded"})
_RECONCILE_GRACE = timedelta(minutes=10)


@dataclass(frozen=True)
class ActionResult:
    action_id: UUID
    state: str
    provider_operation_id: str | None
    deduplicated: bool
    needs_reconcile: bool


def build_intent_key(
    binding: ConnectionBinding, action_type: str, target: str, args: dict[str, Any]
) -> str:
    """A stable key identifying one operator/agent intent (04-DATA §8.4)."""
    return payload_hash(
        {
            "store_id": str(binding.store_id),
            "connection_id": str(binding.connection_id),
            "action_type": action_type,
            "target": target,
            "args": args,
        }
    )


class LocalDurableActionStore:
    """Action + attempt persistence (A02 stand-in) keyed by idempotency intent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, intent_key: str) -> CommerceAction | None:
        return (
            await self._session.exec(
                select(CommerceAction).where(CommerceAction.idempotency_intent_key == intent_key)
            )
        ).first()

    async def create_or_reuse(
        self,
        binding: ConnectionBinding,
        *,
        action_type: str,
        target: str,
        args: dict[str, Any],
        digest: str,
        intent_key: str,
        grant_mode: str,
        currency: str = "",
        amount_minor: int = 0,
    ) -> tuple[CommerceAction, bool]:
        existing = await self.find(intent_key)
        if existing is not None:
            return existing, True
        action = CommerceAction(
            brand_id=binding.brand_id,
            store_id=binding.store_id,
            connection_id=binding.connection_id,
            action_type=action_type,
            target=target,
            arguments_json=json.dumps(args, sort_keys=True, default=str),
            currency=currency,
            amount_minor=amount_minor,
            digest=digest,
            idempotency_intent_key=intent_key,
            grant_mode=grant_mode,
            state="proposed",
        )
        try:
            async with self._session.begin_nested():
                self._session.add(action)
                await self._session.flush()
        except IntegrityError:
            existing = await self.find(intent_key)
            if existing is None:  # pragma: no cover - defensive
                raise
            return existing, True
        return action, False

    async def next_attempt_number(self, action_id: UUID) -> int:
        attempts = (
            await self._session.exec(
                select(CommerceActionAttempt).where(CommerceActionAttempt.action_id == action_id)
            )
        ).all()
        return len(attempts) + 1

    async def record_attempt(
        self,
        action: CommerceAction,
        binding: ConnectionBinding,
        *,
        provider_operation_id: str | None,
        status_category: str,
        outcome_confidence: str,
        retry_classification: str,
        summary: dict[str, Any],
        reconcile_due: bool = False,
    ) -> CommerceActionAttempt:
        attempt = CommerceActionAttempt(
            action_id=action.id,
            attempt_number=await self.next_attempt_number(action.id),
            connector=binding.provider,
            account_ref=binding.account_ref,
            provider_idempotency_key=action.id.hex,
            request_fingerprint=action.digest,
            provider_operation_id=provider_operation_id,
            status_category=status_category,
            outcome_confidence=outcome_confidence,
            retry_classification=retry_classification,
            summary_json=json.dumps(summary, default=str),
            ended_at=utcnow(),
            reconcile_due_at=(utcnow() + _RECONCILE_GRACE) if reconcile_due else None,
        )
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def set_state(
        self,
        action: CommerceAction,
        state: str,
        *,
        provider_operation_id: str | None = None,
        summary: str = "",
        reconcile_due: bool = False,
    ) -> None:
        action.state = state
        if provider_operation_id is not None:
            action.provider_operation_id = provider_operation_id
        if summary:
            action.outcome_summary = summary
        action.reconcile_due_at = (utcnow() + _RECONCILE_GRACE) if reconcile_due else None
        action.updated_at = utcnow()
        self._session.add(action)
        await self._session.flush()


class ActionExecutor:
    """Drives one external write through the durable action contract."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._store = LocalDurableActionStore(session)

    async def execute(
        self,
        binding: ConnectionBinding,
        port: ConnectorPort,
        *,
        action_type: str,
        target: str,
        arguments: dict[str, Any],
        grant_mode: str = "approve",
        currency: str = "",
        amount_minor: int = 0,
    ) -> ActionResult:
        intent_key = build_intent_key(binding, action_type, target, arguments)
        command = ProviderCommand(
            operation=action_type, arguments=arguments, idempotency_intent_key=intent_key
        )
        action, reused = await self._store.create_or_reuse(
            binding,
            action_type=action_type,
            target=target,
            args=arguments,
            digest=command.digest(),
            intent_key=intent_key,
            grant_mode=grant_mode,
            currency=currency,
            amount_minor=amount_minor,
        )

        # I-07: a completed intent never re-dispatches.
        if action.state in _SUCCESS_STATES:
            return ActionResult(action.id, action.state, action.provider_operation_id, True, False)
        # I-08: an ambiguous prior outcome must be reconciled, not retried.
        if action.state == "outcome_unknown":
            return ActionResult(action.id, action.state, action.provider_operation_id, True, True)

        await self._store.set_state(action, "executing")
        try:
            result = await port.execute(command)
        except ConnectorTimeout as exc:
            await self._store.record_attempt(
                action,
                binding,
                provider_operation_id=None,
                status_category="timeout",
                outcome_confidence="unknown",
                retry_classification="reconcile_first",
                summary=exc.to_dict(),
                reconcile_due=True,
            )
            await self._store.set_state(
                action,
                "outcome_unknown",
                reconcile_due=True,
                summary="dispatch timed out; outcome unknown",
            )
            return ActionResult(action.id, "outcome_unknown", None, False, True)
        except ConnectorError as exc:
            state = "failed_retryable" if exc.retryable else "failed_permanent"
            await self._store.record_attempt(
                action,
                binding,
                provider_operation_id=None,
                status_category="error",
                outcome_confidence="failed",
                retry_classification="retryable" if exc.retryable else "permanent",
                summary=exc.to_dict(),
            )
            await self._store.set_state(action, state, summary=exc.message)
            return ActionResult(action.id, state, None, False, False)

        await self._store.record_attempt(
            action,
            binding,
            provider_operation_id=result.provider_operation_id,
            status_category="ok",
            outcome_confidence=result.outcome_confidence,
            retry_classification="none",
            summary=result.summary,
        )
        await self._store.set_state(
            action,
            "succeeded",
            provider_operation_id=result.provider_operation_id,
            summary="confirmed",
        )
        return ActionResult(action.id, "succeeded", result.provider_operation_id, reused, False)

    async def reconcile(
        self, binding: ConnectionBinding, port: ConnectorPort, action_id: UUID
    ) -> ActionResult:
        """Resolve an ``outcome_unknown`` action against the provider (I-08).

        Queries the provider for the side effect; transitions the existing action and
        appends a reconciliation attempt without rewriting prior attempts.
        """
        action = await self._session.get(CommerceAction, action_id)
        if action is None:
            raise ValueError(f"unknown action {action_id}")
        args = json.loads(action.arguments_json)
        command = ProviderCommand(
            operation=action.action_type,
            arguments=args,
            idempotency_intent_key=action.idempotency_intent_key,
        )
        result = await port.reconcile(command)
        if result.outcome_confidence == "confirmed":
            await self._store.record_attempt(
                action,
                binding,
                provider_operation_id=result.provider_operation_id,
                status_category="reconciled",
                outcome_confidence="confirmed",
                retry_classification="none",
                summary={"reconciled": True},
            )
            await self._store.set_state(
                action,
                "reconciled_succeeded",
                provider_operation_id=result.provider_operation_id,
                summary="reconciled: found",
            )
            return ActionResult(
                action.id, "reconciled_succeeded", result.provider_operation_id, False, False
            )
        if result.outcome_confidence == "failed":
            await self._store.record_attempt(
                action,
                binding,
                provider_operation_id=None,
                status_category="reconciled",
                outcome_confidence="failed",
                retry_classification="none",
                summary={"reconciled": True},
            )
            await self._store.set_state(action, "reconciled_failed", summary="reconciled: absent")
            return ActionResult(action.id, "reconciled_failed", None, False, False)
        # Still indeterminate — leave for manual resolution.
        return ActionResult(action.id, "outcome_unknown", None, False, True)
