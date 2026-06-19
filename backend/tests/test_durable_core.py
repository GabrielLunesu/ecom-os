# ruff: noqa: INP001
"""Durable core invariant tests for A02-owned services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401 - ensure all SQLModel tables are registered
from app.actions.service import (
    ActionIntentConflictError,
    ActionValidationError,
    OutcomeUnknownRetryBlockedError,
    create_or_reuse_action,
    finish_attempt,
    reconcile_unknown_action,
    start_attempt,
)
from app.api import activity as activity_api
from app.api.deps import ActorContext
from app.core.time import utcnow
from app.events.durable import (
    InboxVerificationError,
    OutboxLeaseError,
    accept_inbox_event,
    claim_outbox_events,
    enqueue_outbox_event,
    mark_outbox_delivered,
    mark_outbox_failed,
)
from app.jobs.leased import (
    JobLeaseError,
    claim_jobs,
    complete_job,
    enqueue_job,
    fail_job,
    heartbeat_job,
)
from app.models.actions import ActionStateHistory
from app.models.agents import Agent
from app.traces.recorder import (
    add_evidence,
    create_incident,
    create_run,
    create_span,
    create_trace,
    finish_tool_invocation,
    link_evidence,
    list_evidence_for_role,
    record_audit,
    record_tool_invocation,
    search_traces,
)
from app.traces.tools import TraceSearchToolInput, trace_search_tool


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_inbox_accepts_duplicate_source_event_once() -> None:
    async with _session() as session:
        first, created = await accept_inbox_event(
            session,
            event_type="ticket.message.received",
            source="gmail",
            source_scope="connection:inbox-1",
            source_event_id="msg-1",
            payload={"message": "where is my order"},
            coverage="imported",
        )
        second, duplicate_created = await accept_inbox_event(
            session,
            event_type="ticket.message.received",
            source="gmail",
            source_scope="connection:inbox-1",
            source_event_id="msg-1",
            payload={"message": "where is my order"},
            coverage="imported",
        )

        assert created is True
        assert duplicate_created is False
        assert second.id == first.id
        assert second.payload_hash == first.payload_hash


@pytest.mark.asyncio
async def test_outbox_deduplicates_leases_reclaims_and_dead_letters() -> None:
    async with _session() as session:
        event, created = await enqueue_outbox_event(
            session,
            topic="activity.trace.created",
            payload={"trace_id": "trace-1"},
            deduplication_key="trace-created:trace-1",
            max_attempts=2,
        )
        duplicate, duplicate_created = await enqueue_outbox_event(
            session,
            topic="activity.trace.created",
            payload={"trace_id": "trace-1", "ignored": True},
            deduplication_key="trace-created:trace-1",
            max_attempts=2,
        )

        assert created is True
        assert duplicate_created is False
        assert duplicate.id == event.id
        assert duplicate.payload == {"trace_id": "trace-1"}

        claimed = await claim_outbox_events(
            session,
            worker_id="outbox-a",
            topic="activity.trace.created",
            limit=1,
        )
        assert [item.id for item in claimed] == [event.id]
        assert claimed[0].state == "leased"
        assert claimed[0].lease_owner == "outbox-a"
        assert claimed[0].lease_expires_at is not None
        assert claimed[0].attempts == 1

        retry_at = utcnow() + timedelta(minutes=5)
        with pytest.raises(OutboxLeaseError):
            await mark_outbox_failed(
                session,
                claimed[0],
                error="wrong worker",
                worker_id="outbox-b",
            )

        failed = await mark_outbox_failed(
            session,
            claimed[0],
            error="temporary broker outage",
            worker_id="outbox-a",
            retry_at=retry_at,
        )
        assert failed.state == "pending"
        assert failed.attempts == 1
        assert failed.next_run_at == retry_at
        assert failed.lease_owner is None
        assert failed.lease_expires_at is None
        assert failed.last_error == "temporary broker outage"

        assert (
            await claim_outbox_events(
                session,
                worker_id="outbox-b",
                topic="activity.trace.created",
            )
            == []
        )

        failed.next_run_at = utcnow() - timedelta(seconds=1)
        session.add(failed)
        await session.flush()
        reclaimed = await claim_outbox_events(
            session,
            worker_id="outbox-b",
            topic="activity.trace.created",
        )
        assert [item.id for item in reclaimed] == [event.id]
        assert reclaimed[0].attempts == 2

        dead_letter = await mark_outbox_failed(
            session,
            reclaimed[0],
            error="broker outage persisted",
            worker_id="outbox-b",
        )
        assert dead_letter.state == "dead_letter"
        assert dead_letter.attempts == 2
        assert dead_letter.lease_owner is None
        assert dead_letter.lease_expires_at is None
        assert dead_letter.last_error == "broker outage persisted"

        stale_lease, _ = await enqueue_outbox_event(
            session,
            topic="activity.trace.created",
            payload={"trace_id": "trace-2"},
            deduplication_key="trace-created:trace-2",
        )
        first_stale_claim = await claim_outbox_events(
            session,
            worker_id="outbox-c",
            topic="activity.trace.created",
            lease_seconds=-1,
        )
        assert [item.id for item in first_stale_claim] == [stale_lease.id]
        reclaimed_stale = await claim_outbox_events(
            session,
            worker_id="outbox-d",
            topic="activity.trace.created",
        )
        assert [item.id for item in reclaimed_stale] == [stale_lease.id]
        assert reclaimed_stale[0].lease_owner == "outbox-d"
        assert reclaimed_stale[0].attempts == 2

        delivered = await mark_outbox_delivered(
            session,
            reclaimed_stale[0],
            worker_id="outbox-d",
        )
        assert delivered.state == "delivered"
        assert delivered.lease_owner is None
        assert delivered.lease_expires_at is None
        assert delivered.delivered_at is not None


@pytest.mark.asyncio
async def test_inbox_rejects_unverified_event_before_acceptance() -> None:
    async with _session() as session:
        with pytest.raises(InboxVerificationError):
            await accept_inbox_event(
                session,
                event_type="ticket.message.received",
                source="gmail",
                source_event_id="msg-2",
                payload={"message": "bad signature"},
                verification="invalid",
            )


@pytest.mark.asyncio
async def test_leased_jobs_reclaim_expired_lease_and_dead_letter_after_retry_cap() -> None:
    async with _session() as session:
        job, created = await enqueue_job(
            session,
            job_type="ticket.workflow",
            payload={"ticket_id": "t-1"},
            deduplication_key="ticket:t-1",
            concurrency_key="ticket:t-1",
            max_attempts=2,
        )
        duplicate, duplicate_created = await enqueue_job(
            session,
            job_type="ticket.workflow",
            payload={"ticket_id": "t-1"},
            deduplication_key="ticket:t-1",
            concurrency_key="ticket:t-1",
            max_attempts=2,
        )

        assert created is True
        assert duplicate_created is False
        assert duplicate.id == job.id

        claimed = await claim_jobs(session, worker_id="worker-a", lease_seconds=1)
        assert [item.id for item in claimed] == [job.id]
        assert claimed[0].attempts == 1

        claimed[0].lease_expires_at = utcnow() - timedelta(seconds=1)
        session.add(claimed[0])
        await session.flush()

        reclaimed = await claim_jobs(session, worker_id="worker-b", lease_seconds=60)
        assert [item.id for item in reclaimed] == [job.id]
        assert reclaimed[0].lease_owner == "worker-b"
        assert reclaimed[0].attempts == 2

        failed = await fail_job(
            session,
            reclaimed[0],
            worker_id="worker-b",
            error_code="connector_unavailable",
            error="provider down",
            retryable=True,
        )
        assert failed.state == "dead_letter"


@pytest.mark.asyncio
async def test_leased_jobs_heartbeat_completion_concurrency_and_retry() -> None:
    async with _session() as session:
        primary, _ = await enqueue_job(
            session,
            job_type="ticket.workflow",
            payload={"ticket_id": "t-1"},
            deduplication_key="ticket:t-1",
            concurrency_key="ticket:t-shared",
            max_attempts=3,
        )
        blocked_by_concurrency, _ = await enqueue_job(
            session,
            job_type="ticket.workflow",
            payload={"ticket_id": "t-2"},
            deduplication_key="ticket:t-2",
            concurrency_key="ticket:t-shared",
            max_attempts=3,
        )
        independent, _ = await enqueue_job(
            session,
            job_type="ticket.workflow",
            payload={"ticket_id": "t-3"},
            deduplication_key="ticket:t-3",
            concurrency_key="ticket:t-3",
            max_attempts=3,
        )

        claimed = await claim_jobs(
            session,
            worker_id="worker-a",
            job_type="ticket.workflow",
            limit=3,
            lease_seconds=30,
        )

        assert [item.id for item in claimed] == [primary.id, independent.id]
        assert blocked_by_concurrency.state == "queued"
        assert primary.attempts == 1
        assert independent.attempts == 1

        with pytest.raises(JobLeaseError):
            await heartbeat_job(
                session,
                primary,
                worker_id="worker-b",
                lease_seconds=60,
            )

        heartbeat = await heartbeat_job(
            session,
            primary,
            worker_id="worker-a",
            lease_seconds=60,
        )
        assert heartbeat.lease_owner == "worker-a"
        assert heartbeat.heartbeat_at is not None
        assert heartbeat.lease_expires_at is not None
        assert heartbeat.lease_expires_at > heartbeat.heartbeat_at

        retryable = await fail_job(
            session,
            independent,
            worker_id="worker-a",
            error_code="provider_rate_limited",
            error="rate limited",
            retryable=True,
            retry_delay_seconds=300,
        )
        assert retryable.state == "failed_retryable"
        assert retryable.lease_owner is None
        assert retryable.lease_expires_at is None
        assert retryable.heartbeat_at is None
        assert retryable.next_run_at > utcnow()

        assert (
            await claim_jobs(
                session,
                worker_id="worker-b",
                job_type="ticket.workflow",
                limit=3,
            )
            == []
        )

        completed = await complete_job(session, primary, worker_id="worker-a")
        assert completed.state == "succeeded"
        assert completed.completed_at is not None
        assert completed.lease_owner is None
        assert completed.lease_expires_at is None

        unblocked = await claim_jobs(
            session,
            worker_id="worker-b",
            job_type="ticket.workflow",
            limit=3,
        )
        assert [item.id for item in unblocked] == [blocked_by_concurrency.id]
        assert unblocked[0].lease_owner == "worker-b"
        assert unblocked[0].attempts == 1

        with pytest.raises(JobLeaseError):
            await complete_job(session, completed, worker_id="worker-a")


@pytest.mark.asyncio
async def test_trace_tool_invocation_search_and_role_filtered_evidence() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="ticket_run",
            title="WISMO ticket",
            root_actor_type="service",
            root_actor_id="worker",
            primary_entity_type="ticket",
            primary_entity_id="ticket-123",
            coverage="verified",
        )
        run = await create_run(session, trace_id=trace.id, runtime="hermes", coverage="observed")
        span = await create_span(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_type="tool",
            name="ecom.ticket.get",
            coverage="verified",
        )
        invocation = await record_tool_invocation(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_id=span.id,
            tool_name="ecom.ticket.get",
            tool_version="1.0.0",
            schema_hash="sha256:schema",
            transport="hermes_adapter",
            actor_type="service",
            actor_id="adapter",
            arguments_redacted={"ticket_id": "ticket-123"},
        )
        internal = await add_evidence(
            session,
            evidence_type="ticket_message",
            source="gmail",
            source_id="msg-1",
            trust_label="untrusted_customer_content",
            access_label="internal",
            excerpt="Where is my order?",
        )
        finance = await add_evidence(
            session,
            evidence_type="order_margin",
            source="shopify",
            source_id="order-1",
            trust_label="provider_payload",
            access_label="financial_sensitive",
            excerpt="Contribution margin input",
        )
        await link_evidence(
            session,
            evidence_id=internal.id,
            target_type="tool_invocation",
            target_id=invocation.id,
            purpose="input",
        )
        await link_evidence(
            session,
            evidence_id=finance.id,
            target_type="tool_invocation",
            target_id=invocation.id,
            purpose="support",
        )

        found = await search_traces(
            session,
            entity_type="ticket",
            entity_id="ticket-123",
            coverage="verified",
        )
        viewer_evidence = await list_evidence_for_role(
            session,
            role="viewer",
            target_type="tool_invocation",
            target_id=invocation.id,
        )
        finance_evidence = await list_evidence_for_role(
            session,
            role="finance",
            target_type="tool_invocation",
            target_id=invocation.id,
        )

        assert [item.id for item in found] == [trace.id]
        assert {item.id for item in viewer_evidence} == {internal.id}
        assert {item.id for item in finance_evidence} == {internal.id, finance.id}


@pytest.mark.asyncio
async def test_trace_recorder_rejects_secret_bearing_tool_and_evidence_fields() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="ticket_run",
            title="Secret guard",
            root_actor_type="service",
            root_actor_id="worker",
            coverage="verified",
        )
        run = await create_run(session, trace_id=trace.id, runtime="hermes", coverage="observed")
        span = await create_span(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_type="tool",
            name="ecom.ticket.get",
            coverage="verified",
        )

        with pytest.raises(ValueError, match="arguments must be redacted"):
            await record_tool_invocation(
                session,
                trace_id=trace.id,
                run_id=run.id,
                span_id=span.id,
                tool_name="ecom.ticket.get",
                tool_version="1.0.0",
                schema_hash="sha256:schema",
                transport="hermes_adapter",
                actor_type="service",
                actor_id="adapter",
                arguments_redacted={"nested": {"token": "plaintext"}},
            )

        invocation = await record_tool_invocation(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_id=span.id,
            tool_name="ecom.ticket.get",
            tool_version="1.0.0",
            schema_hash="sha256:schema",
            transport="hermes_adapter",
            actor_type="service",
            actor_id="adapter",
            arguments_redacted={"ticket_id": "ticket-123"},
        )

        with pytest.raises(ValueError, match="results must be redacted"):
            await finish_tool_invocation(
                session,
                invocation,
                status="succeeded",
                result_summary={"authorization": "Bearer plaintext"},
            )

        with pytest.raises(ValueError, match="secret evidence"):
            await add_evidence(
                session,
                evidence_type="credential",
                source="connector",
                source_id="credential-1",
                trust_label="system_record",
                access_label="secret",
                excerpt="must not persist",
            )

        with pytest.raises(ValueError, match="metadata"):
            await add_evidence(
                session,
                evidence_type="connector_payload",
                source="connector",
                source_id="payload-1",
                trust_label="provider_payload",
                access_label="internal",
                metadata={"safe": {"password": "plaintext"}},
            )


@pytest.mark.asyncio
async def test_trace_search_tool_filters_evidence_before_agent_context() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="ticket_run",
            title="WISMO ticket",
            root_actor_type="service",
            root_actor_id="worker",
            primary_entity_type="ticket",
            primary_entity_id="ticket-456",
            coverage="verified",
        )
        await create_trace(
            session,
            trace_type="ticket_run",
            title="Other ticket",
            root_actor_type="service",
            root_actor_id="worker",
            primary_entity_type="ticket",
            primary_entity_id="ticket-other",
            coverage="verified",
        )
        run = await create_run(session, trace_id=trace.id, runtime="hermes", coverage="observed")
        span = await create_span(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_type="tool",
            name="ecom.ticket.reply",
            coverage="verified",
        )
        invocation = await record_tool_invocation(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_id=span.id,
            tool_name="ecom.ticket.reply",
            tool_version="1.0.0",
            schema_hash="sha256:schema",
            transport="hermes_adapter",
            actor_type="service",
            actor_id="adapter",
            arguments_redacted={"ticket_id": "ticket-456"},
        )
        public = await add_evidence(
            session,
            evidence_type="trace_summary",
            source="ecom_os",
            source_id="summary-1",
            trust_label="system_record",
            access_label="public",
            excerpt="Public trace summary",
        )
        internal = await add_evidence(
            session,
            evidence_type="ticket_message",
            source="gmail",
            source_id="msg-456",
            trust_label="untrusted_customer_content",
            access_label="internal",
            excerpt="Customer asked about delivery",
        )
        finance = await add_evidence(
            session,
            evidence_type="order_margin",
            source="shopify",
            source_id="order-456",
            trust_label="provider_payload",
            access_label="financial_sensitive",
            excerpt="Margin should not reach viewer tools",
        )
        await link_evidence(
            session,
            evidence_id=public.id,
            target_type="trace",
            target_id=trace.id,
            purpose="summary",
        )
        await link_evidence(
            session,
            evidence_id=internal.id,
            target_type="tool_invocation",
            target_id=invocation.id,
            purpose="input",
        )
        await link_evidence(
            session,
            evidence_id=finance.id,
            target_type="trace",
            target_id=trace.id,
            purpose="impact",
        )
        await link_evidence(
            session,
            evidence_id=finance.id,
            target_type="tool_invocation",
            target_id=invocation.id,
            purpose="support",
        )

        viewer_result = await trace_search_tool(
            session,
            TraceSearchToolInput(
                role="viewer",
                entity_type="ticket",
                entity_id="ticket-456",
                coverage="verified",
                limit=1,
            ),
        )
        finance_result = await trace_search_tool(
            session,
            TraceSearchToolInput(
                role="finance",
                entity_type="ticket",
                entity_id="ticket-456",
                coverage="verified",
            ),
        )
        public_only_result = await trace_search_tool(
            session,
            TraceSearchToolInput(
                role="unmapped",
                entity_type="ticket",
                entity_id="ticket-456",
                coverage="verified",
            ),
        )
        no_evidence_result = await trace_search_tool(
            session,
            TraceSearchToolInput(
                role="finance",
                entity_type="ticket",
                entity_id="ticket-456",
                coverage="verified",
                include_evidence=False,
            ),
        )

        assert viewer_result.filters["entity_id"] == "ticket-456"
        assert [item.trace.id for item in viewer_result.results] == [trace.id]
        assert {item.id for item in viewer_result.results[0].evidence} == {
            public.id,
            internal.id,
        }
        assert {item.id for item in finance_result.results[0].evidence} == {
            public.id,
            internal.id,
            finance.id,
        }
        assert [item.id for item in finance_result.results[0].evidence].count(finance.id) == 1
        assert {item.id for item in public_only_result.results[0].evidence} == {public.id}
        assert no_evidence_result.results[0].evidence == []

        with pytest.raises(ValueError, match="limit"):
            await trace_search_tool(session, TraceSearchToolInput(limit=0))


@pytest.mark.asyncio
async def test_action_duplicate_intent_outcome_unknown_blocks_retry_until_reconciled() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="action",
            title="Send reply",
            root_actor_type="service",
            root_actor_id="worker",
            coverage="verified",
        )
        store_id = uuid4()
        connection_id = uuid4()
        action, created = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=store_id,
            connection_id=connection_id,
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={
                "body_hash": "sha256:body",
                "recipient": "customer@example.test",
            },
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="unrestricted",
            intent_key="ticket-123:msg-1:sha256:body",
        )
        duplicate, duplicate_created = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=store_id,
            connection_id=connection_id,
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={
                "body_hash": "sha256:body",
                "recipient": "customer@example.test",
            },
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="unrestricted",
            intent_key="ticket-123:msg-1:sha256:body",
        )

        assert created is True
        assert duplicate_created is False
        assert duplicate.id == action.id

        attempt = await start_attempt(
            session,
            action,
            connector="fake_inbox",
            provider_idempotency_key=f"reply:{action.id}:1",
            safe_request_summary={"recipient": "customer@example.test"},
        )
        await finish_attempt(
            session,
            action,
            attempt,
            outcome_state="outcome_unknown",
            http_status_category="timeout",
            retry_classification="ambiguous_after_dispatch",
            outcome_confidence="unknown",
            error_reference="timeout after request dispatch",
        )

        with pytest.raises(OutcomeUnknownRetryBlockedError):
            await start_attempt(
                session,
                action,
                connector="fake_inbox",
                provider_idempotency_key=f"reply:{action.id}:2",
                safe_request_summary={"recipient": "customer@example.test"},
            )

        reconciled = await reconcile_unknown_action(
            session,
            action,
            reconciled_state="reconciled_succeeded",
            evidence={"provider_message_id": "pm-1"},
        )
        assert reconciled.state == "reconciled_succeeded"

        rows = list(
            (
                await session.exec(
                    select(ActionStateHistory).where(ActionStateHistory.action_id == action.id)
                )
            ).all()
        )
        assert [row.to_state for row in rows] == [
            "proposed",
            "executing",
            "outcome_unknown",
            "reconciled_succeeded",
        ]


@pytest.mark.asyncio
async def test_action_requires_exact_scope_and_rejects_conflicting_intent() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="action",
            title="Send reply",
            root_actor_type="service",
            root_actor_id="worker",
            coverage="verified",
        )
        store_id = uuid4()
        connection_id = uuid4()

        with pytest.raises(ActionValidationError, match="store_id and connection_id"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=None,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"body_hash": "sha256:body"},
                requested_actor_type="user",
                requested_actor_id="owner-1",
                autonomy_mode="approve",
                intent_key="ticket-123:reply-validation",
            )

        with pytest.raises(ActionValidationError, match="requested actor"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=store_id,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"body_hash": "sha256:body"},
                requested_actor_type="user",
                requested_actor_id="",
                autonomy_mode="approve",
                intent_key="ticket-123:reply-validation",
            )

        with pytest.raises(ActionValidationError, match="intent_key"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=store_id,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"body_hash": "sha256:body"},
                requested_actor_type="user",
                requested_actor_id="owner-1",
                autonomy_mode="approve",
                intent_key="",
            )

        action, created = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=store_id,
            connection_id=connection_id,
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={"body_hash": "sha256:body"},
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="approve",
            intent_key="ticket-123:reply-validation",
        )

        assert created is True
        assert action.store_id == store_id
        assert action.connection_id == connection_id
        assert action.requested_actor_type == "user"
        assert action.requested_actor_id == "owner-1"

        with pytest.raises(ActionIntentConflictError, match="different digest"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=store_id,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"body_hash": "sha256:changed-body"},
                requested_actor_type="user",
                requested_actor_id="owner-1",
                autonomy_mode="approve",
                intent_key="ticket-123:reply-validation",
            )


@pytest.mark.asyncio
async def test_action_service_rejects_secret_bearing_arguments_and_evidence() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="action",
            title="Secret action guard",
            root_actor_type="service",
            root_actor_id="worker",
            coverage="verified",
        )
        store_id = uuid4()
        connection_id = uuid4()

        with pytest.raises(ActionValidationError, match="arguments"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=store_id,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"nested": {"token": "plaintext"}},
                requested_actor_type="user",
                requested_actor_id="owner-1",
                autonomy_mode="approve",
                intent_key="ticket-123:secret-args",
            )

        with pytest.raises(ActionValidationError, match="grant"):
            await create_or_reuse_action(
                session,
                trace_id=trace.id,
                action_type="ticket.reply.send",
                schema_version=1,
                store_id=store_id,
                connection_id=connection_id,
                target_type="ticket",
                target_id="ticket-123",
                normalized_arguments={"body_hash": "sha256:body"},
                requested_actor_type="user",
                requested_actor_id="owner-1",
                autonomy_mode="approve",
                intent_key="ticket-123:secret-grant",
                effective_grant={"credential": "plaintext"},
            )

        action, _ = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=store_id,
            connection_id=connection_id,
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={"body_hash": "sha256:body"},
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="approve",
            intent_key="ticket-123:secret-summary",
        )

        with pytest.raises(ActionValidationError, match="request summary"):
            await start_attempt(
                session,
                action,
                connector="fake_inbox",
                provider_idempotency_key=f"reply:{action.id}:secret-request",
                safe_request_summary={"authorization": "Bearer plaintext"},
            )

        attempt = await start_attempt(
            session,
            action,
            connector="fake_inbox",
            provider_idempotency_key=f"reply:{action.id}:1",
            safe_request_summary={"recipient": "customer@example.test"},
        )

        with pytest.raises(ActionValidationError, match="response summary"):
            await finish_attempt(
                session,
                action,
                attempt,
                outcome_state="succeeded",
                safe_response_summary={"api_key": "plaintext"},
            )

        await finish_attempt(
            session,
            action,
            attempt,
            outcome_state="outcome_unknown",
            http_status_category="timeout",
            retry_classification="ambiguous_after_dispatch",
            outcome_confidence="unknown",
            error_reference="timeout after request dispatch",
        )

        with pytest.raises(ActionValidationError, match="reconciliation evidence"):
            await reconcile_unknown_action(
                session,
                action,
                reconciled_state="manual_resolution",
                evidence={"secret": "plaintext"},
            )


@pytest.mark.asyncio
async def test_activity_trace_detail_filters_evidence_by_actor_role() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="ticket_run",
            title="WISMO ticket",
            root_actor_type="service",
            root_actor_id="worker",
            primary_entity_type="ticket",
            primary_entity_id="ticket-123",
            coverage="verified",
        )
        run = await create_run(session, trace_id=trace.id, runtime="hermes", coverage="observed")
        span = await create_span(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_type="tool",
            name="ecom.ticket.reply",
            coverage="verified",
        )
        invocation = await record_tool_invocation(
            session,
            trace_id=trace.id,
            run_id=run.id,
            span_id=span.id,
            tool_name="ecom.ticket.reply",
            tool_version="1.0.0",
            schema_hash="sha256:schema",
            transport="hermes_adapter",
            actor_type="service",
            actor_id="adapter",
            arguments_redacted={"ticket_id": "ticket-123"},
        )
        store_id = uuid4()
        connection_id = uuid4()
        action, _ = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=store_id,
            connection_id=connection_id,
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={"body_hash": "sha256:body"},
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="approve",
            intent_key="ticket-123:reply-1",
        )
        internal = await add_evidence(
            session,
            evidence_type="ticket_message",
            source="gmail",
            source_id="msg-1",
            trust_label="untrusted_customer_content",
            access_label="internal",
            excerpt="Where is my order?",
        )
        finance = await add_evidence(
            session,
            evidence_type="margin_input",
            source="shopify",
            source_id="order-1",
            trust_label="provider_payload",
            access_label="financial_sensitive",
            excerpt="Margin evidence",
        )
        await link_evidence(
            session,
            evidence_id=internal.id,
            target_type="tool_invocation",
            target_id=invocation.id,
            purpose="input",
        )
        await link_evidence(
            session,
            evidence_id=finance.id,
            target_type="action",
            target_id=action.id,
            purpose="outcome",
        )

        viewer_detail = await activity_api.get_trace_detail(
            trace.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="viewer",
                    identity_profile={"role": "viewer"},
                ),
            ),
        )
        finance_detail = await activity_api.get_trace_detail(
            trace.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="finance",
                    identity_profile={"role": "finance"},
                ),
            ),
        )

        assert viewer_detail.trace.id == trace.id
        assert [item.id for item in viewer_detail.tool_invocations] == [invocation.id]
        assert {item.id for item in viewer_detail.evidence} == {internal.id}
        assert {item.id for item in finance_detail.evidence} == {
            internal.id,
            finance.id,
        }


@pytest.mark.asyncio
async def test_activity_action_detail_includes_attempts_history_and_filtered_evidence() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="action",
            title="Send reply",
            root_actor_type="service",
            root_actor_id="worker",
            coverage="verified",
        )
        action, _ = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=uuid4(),
            connection_id=uuid4(),
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={"body_hash": "sha256:body"},
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="approve",
            intent_key="ticket-123:reply-2",
        )
        attempt = await start_attempt(
            session,
            action,
            connector="fake_inbox",
            provider_idempotency_key=f"reply:{action.id}:1",
            safe_request_summary={"recipient": "customer@example.test"},
        )
        await finish_attempt(
            session,
            action,
            attempt,
            outcome_state="succeeded",
            http_status_category="2xx",
            safe_response_summary={"provider_message_id": "pm-1"},
            provider_operation_id="pm-1",
            outcome_confidence="confirmed",
        )
        internal = await add_evidence(
            session,
            evidence_type="provider_receipt",
            source="fake_inbox",
            source_id="pm-1",
            trust_label="provider_payload",
            access_label="internal",
            excerpt="Message accepted",
        )
        finance = await add_evidence(
            session,
            evidence_type="financial_note",
            source="shopify",
            source_id="order-1",
            trust_label="provider_payload",
            access_label="financial_sensitive",
            excerpt="Finance-only note",
        )
        for evidence in (internal, finance):
            await link_evidence(
                session,
                evidence_id=evidence.id,
                target_type="action",
                target_id=action.id,
                purpose="outcome",
            )

        detail = await activity_api.get_action_detail(
            action.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="viewer",
                    identity_profile={"role": "viewer"},
                ),
            ),
        )

        assert detail.action.id == action.id
        assert [item.provider_operation_id for item in detail.attempts] == ["pm-1"]
        assert [item.to_state for item in detail.history] == [
            "proposed",
            "executing",
            "succeeded",
        ]
        assert {item.id for item in detail.evidence} == {internal.id}

        with pytest.raises(HTTPException) as exc_info:
            await activity_api.get_action_detail(
                uuid4(),
                session=session,
                actor=ActorContext(
                    actor_type="agent",
                    agent=Agent(gateway_id=uuid4(), name="viewer"),
                ),
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_activity_incident_detail_includes_context_and_filtered_evidence() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="webhook_dispatch",
            title="Webhook delivery failed",
            root_actor_type="service",
            root_actor_id="webhook-worker",
            primary_entity_type="webhook_payload",
            primary_entity_id="payload-123",
            coverage="verified",
        )
        action, _ = await create_or_reuse_action(
            session,
            trace_id=trace.id,
            action_type="ticket.reply.send",
            schema_version=1,
            store_id=uuid4(),
            connection_id=uuid4(),
            target_type="ticket",
            target_id="ticket-123",
            normalized_arguments={"body_hash": "sha256:body"},
            requested_actor_type="user",
            requested_actor_id="owner-1",
            autonomy_mode="approve",
            intent_key="ticket-123:reply-incident",
        )
        incident = await create_incident(
            session,
            title="Webhook dispatch degraded",
            severity="high",
            detection_source="durable_job_dead_letter",
            root_trace_id=trace.id,
            metadata={"job_id": "job-1"},
        )
        internal = await add_evidence(
            session,
            evidence_type="worker_log_excerpt",
            source="durable_jobs",
            source_id="job-1",
            trust_label="ecom_controlled",
            access_label="internal",
            excerpt="Delivery dead-lettered after retry cap",
        )
        finance = await add_evidence(
            session,
            evidence_type="margin_impact",
            source="shopify",
            source_id="order-1",
            trust_label="provider_payload",
            access_label="financial_sensitive",
            excerpt="Finance-only incident impact",
        )
        await link_evidence(
            session,
            evidence_id=internal.id,
            target_type="incident",
            target_id=incident.id,
            purpose="diagnosis",
        )
        await link_evidence(
            session,
            evidence_id=finance.id,
            target_type="action",
            target_id=action.id,
            purpose="impact",
        )

        viewer_detail = await activity_api.get_incident_detail(
            incident.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="viewer",
                    identity_profile={"role": "viewer"},
                ),
            ),
        )
        finance_detail = await activity_api.get_incident_detail(
            incident.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="finance",
                    identity_profile={"role": "finance"},
                ),
            ),
        )

        assert viewer_detail.incident.id == incident.id
        assert viewer_detail.root_trace is not None
        assert viewer_detail.root_trace.id == trace.id
        assert [item.id for item in viewer_detail.related_actions] == [action.id]
        assert {item.id for item in viewer_detail.evidence} == {internal.id}
        assert {item.id for item in finance_detail.evidence} == {
            internal.id,
            finance.id,
        }

        with pytest.raises(HTTPException) as exc_info:
            await activity_api.get_incident_detail(
                uuid4(),
                session=session,
                actor=ActorContext(
                    actor_type="agent",
                    agent=Agent(gateway_id=uuid4(), name="viewer"),
                ),
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_audit_records_reject_secret_fields_and_require_privileged_reader() -> None:
    async with _session() as session:
        trace = await create_trace(
            session,
            trace_type="grant_change",
            title="Grant changed",
            root_actor_type="user",
            root_actor_id="owner-1",
            coverage="verified",
        )
        audit = await record_audit(
            session,
            trace_id=trace.id,
            actor_type="user",
            actor_id="owner-1",
            action="grant.updated",
            target_type="grant",
            target_id="grant-1",
            before={"mode": "approve"},
            after={"mode": "policy"},
            reason="owner updated automation mode",
        )

        detail = await activity_api.get_audit_record(
            audit.id,
            session=session,
            actor=ActorContext(
                actor_type="agent",
                agent=Agent(
                    gateway_id=uuid4(),
                    name="operator",
                    identity_profile={"role": "operator"},
                ),
            ),
        )

        assert detail.id == audit.id
        assert detail.trace_id == trace.id
        assert detail.before == {"mode": "approve"}
        assert detail.after == {"mode": "policy"}

        with pytest.raises(HTTPException) as forbidden:
            await activity_api.get_audit_record(
                audit.id,
                session=session,
                actor=ActorContext(
                    actor_type="agent",
                    agent=Agent(
                        gateway_id=uuid4(),
                        name="viewer",
                        identity_profile={"role": "viewer"},
                    ),
                ),
            )
        assert forbidden.value.status_code == 403

        with pytest.raises(HTTPException) as missing:
            await activity_api.get_audit_record(
                uuid4(),
                session=session,
                actor=ActorContext(
                    actor_type="agent",
                    agent=Agent(
                        gateway_id=uuid4(),
                        name="operator",
                        identity_profile={"role": "operator"},
                    ),
                ),
            )
        assert missing.value.status_code == 404

        with pytest.raises(ValueError, match="secret-bearing"):
            await record_audit(
                session,
                actor_type="user",
                actor_id="owner-1",
                action="secret.updated",
                target_type="connection",
                target_id="connection-1",
                before={"nested": {"token": "plaintext"}},
                after={"nested": {"token": "new-plaintext"}},
            )
