# ruff: noqa
"""A04 — durable write idempotency, outcome_unknown, and reconciliation."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import func, select

from app.connectors.actions import ActionExecutor
from app.connectors.adapters.fake import FakeCommerceAdapter, FakeProviderBackend
from app.connectors.binding import ConnectionBinding
from app.connectors.models import CommerceAction, CommerceActionAttempt
from tests.a04_helpers import open_session


def _binding(account="store-A"):
    return ConnectionBinding(
        brand_id=uuid4(),
        store_id=uuid4(),
        connection_id=uuid4(),
        provider="fake",
        capability="store",
        account_ref=account,
        adapter_version="v1",
    )


ARGS = {"title": "VIP", "percentage": 10.0, "code": "VIP10"}


@pytest.mark.asyncio
async def test_duplicate_intent_executes_side_effect_once() -> None:
    async with open_session() as session:
        backend = FakeProviderBackend("store-A")
        binding = _binding("store-A")
        port = FakeCommerceAdapter(binding, backend)
        ex = ActionExecutor(session)

        r1 = await ex.execute(
            binding, port, action_type="create_discount", target="discount:VIP10", arguments=ARGS
        )
        r2 = await ex.execute(
            binding, port, action_type="create_discount", target="discount:VIP10", arguments=ARGS
        )
        await session.commit()

        assert r1.state == "succeeded" and r1.provider_operation_id
        assert r2.deduplicated is True and r2.state == "succeeded"
        # Exactly one action row and one landed side effect (I-06/I-07).
        actions = int((await session.exec(select(func.count()).select_from(CommerceAction))).one())
        assert actions == 1
        assert backend.execute_calls == 1  # the second call never re-dispatched
        assert len(backend.landed) == 1


@pytest.mark.asyncio
async def test_wrong_account_write_fails_closed() -> None:
    async with open_session() as session:
        backend = FakeProviderBackend("real-account")
        binding = _binding("spoofed-account")  # bound to the wrong account
        port = FakeCommerceAdapter(binding, backend)
        ex = ActionExecutor(session)

        result = await ex.execute(
            binding, port, action_type="create_discount", target="discount:VIP10", arguments=ARGS
        )
        await session.commit()
        # No side effect landed; the action is permanently failed with a reason.
        assert result.state == "failed_permanent"
        assert backend.landed == {}
        attempt = (await session.exec(select(CommerceActionAttempt))).first()
        assert attempt.outcome_confidence == "failed"
        assert attempt.status_category == "error"


@pytest.mark.asyncio
async def test_timeout_after_acceptance_reconciles_without_duplicate() -> None:
    async with open_session() as session:
        # The provider accepts the write but the response times out.
        backend = FakeProviderBackend("store-A", fail_mode="timeout")
        binding = _binding("store-A")
        port = FakeCommerceAdapter(binding, backend)
        ex = ActionExecutor(session)

        first = await ex.execute(
            binding, port, action_type="create_discount", target="discount:VIP10", arguments=ARGS
        )
        await session.commit()
        assert first.state == "outcome_unknown" and first.needs_reconcile is True

        # A blind retry must NOT re-dispatch while outcome is unknown (I-08).
        retry = await ex.execute(
            binding, port, action_type="create_discount", target="discount:VIP10", arguments=ARGS
        )
        assert retry.state == "outcome_unknown" and retry.deduplicated is True
        assert backend.execute_calls == 1  # still only the original dispatch

        # Reconcile: the side effect is found upstream and the action resolves.
        resolved = await ex.reconcile(binding, port, first.action_id)
        await session.commit()
        assert resolved.state == "reconciled_succeeded"
        assert resolved.provider_operation_id is not None
        assert backend.execute_calls == 1  # reconcile does not repeat the write
        assert len(backend.landed) == 1

        # Attempts are append-only: the timeout attempt + the reconciliation attempt.
        attempts = (
            await session.exec(
                select(CommerceActionAttempt).where(
                    CommerceActionAttempt.action_id == first.action_id
                )
            )
        ).all()
        assert len(attempts) == 2
        assert {a.outcome_confidence for a in attempts} == {"unknown", "confirmed"}


@pytest.mark.asyncio
async def test_reconcile_reports_absent_side_effect() -> None:
    async with open_session() as session:
        backend = FakeProviderBackend("store-A")
        binding = _binding("store-A")
        port = FakeCommerceAdapter(binding, backend)
        ex = ActionExecutor(session)
        # Manufacture an outcome_unknown action whose side effect never landed.
        from app.connectors.actions import build_intent_key
        from app.connectors.models import CommerceAction

        intent = build_intent_key(binding, "create_discount", "discount:GONE", ARGS)
        action = CommerceAction(
            brand_id=binding.brand_id,
            store_id=binding.store_id,
            connection_id=binding.connection_id,
            action_type="create_discount",
            target="discount:GONE",
            arguments_json=__import__("json").dumps(ARGS),
            digest="d",
            idempotency_intent_key=intent,
            state="outcome_unknown",
        )
        session.add(action)
        await session.flush()

        resolved = await ex.reconcile(binding, port, action.id)
        await session.commit()
        assert resolved.state == "reconciled_failed"
