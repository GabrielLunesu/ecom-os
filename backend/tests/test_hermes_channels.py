"""Tests for native channel + cron delivery contracts (Runtime Spec §12, §15.5).

Proves: identity mapping resolves (and an unmapped user gets no identity), delivery is
idempotent per brief/date/channel, a failure is visible and retryable, and cron scheduling
returns a reference.
"""

from __future__ import annotations

import pytest

from app.hermes.channels import (
    ChannelDeliveryService,
    DeliveryIntent,
    DeliveryStatus,
    FakeChannelTransport,
    FakeDeliveryLog,
    FakeIdentityResolver,
    FakeScheduler,
    MappedIdentity,
)


def _intent(channel: str = "telegram") -> DeliveryIntent:
    return DeliveryIntent(
        brief_id="brief_2026_06_18",
        brief_date="2026-06-18",
        channel=channel,
        target="chat_123",
        body_hash="sha256:abc",
    )


# --- identity mapping (I-09) -------------------------------------------------
@pytest.mark.asyncio
async def test_mapped_identity_resolves() -> None:
    resolver = FakeIdentityResolver(
        {
            ("telegram", "tg_user_1"): MappedIdentity(
                channel="telegram",
                external_user_id="tg_user_1",
                ecom_user_id="usr_1",
                access_label="operator",
            )
        }
    )
    identity = await resolver.resolve("telegram", "tg_user_1")
    assert identity is not None
    assert identity.ecom_user_id == "usr_1"


@pytest.mark.asyncio
async def test_unmapped_identity_gets_no_privileged_identity() -> None:
    resolver = FakeIdentityResolver({})
    assert await resolver.resolve("telegram", "stranger") is None


# --- idempotent delivery (§12.3, §15.5) --------------------------------------
@pytest.mark.asyncio
async def test_delivery_sends_once() -> None:
    transport = FakeChannelTransport()
    service = ChannelDeliveryService(transport, FakeDeliveryLog())
    receipt = await service.deliver(_intent())
    assert receipt.status is DeliveryStatus.delivered
    assert receipt.provider_message_id == "msg_1"
    assert len(transport.sends) == 1


@pytest.mark.asyncio
async def test_repeated_delivery_does_not_duplicate() -> None:
    transport = FakeChannelTransport()
    log = FakeDeliveryLog()
    service = ChannelDeliveryService(transport, log)

    first = await service.deliver(_intent())
    second = await service.deliver(_intent())  # same brief/date/channel

    assert first.status is DeliveryStatus.delivered
    assert second.status is DeliveryStatus.duplicate
    assert second.provider_message_id == first.provider_message_id
    assert len(transport.sends) == 1  # only one real send


@pytest.mark.asyncio
async def test_delivery_failure_is_visible_and_retryable() -> None:
    transport = FakeChannelTransport(fail_times=1)
    log = FakeDeliveryLog()
    service = ChannelDeliveryService(transport, log)

    failed = await service.deliver(_intent())
    assert failed.status is DeliveryStatus.failed
    assert failed.retryable is True
    assert failed.error is not None

    # Retry succeeds because the failure was not logged as delivered.
    retried = await service.deliver(_intent())
    assert retried.status is DeliveryStatus.delivered
    assert len(transport.sends) == 1


# --- cron scheduling (§12.3) -------------------------------------------------
@pytest.mark.asyncio
async def test_schedule_returns_reference() -> None:
    scheduler = FakeScheduler()
    ref = await scheduler.schedule(cron="0 7 * * *", task_ref="ecom.daily_brief.get")
    assert ref.schedule_id in scheduler.schedules
    assert ref.cron == "0 7 * * *"
    await scheduler.cancel(ref.schedule_id)
    assert ref.schedule_id not in scheduler.schedules
