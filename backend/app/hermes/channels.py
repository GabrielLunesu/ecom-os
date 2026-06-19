"""Native channel + cron delivery contracts (Runtime Spec §12, AGENTS I-17).

Hermes owns the channel transports (Telegram/Slack/Discord/email) and cron. Ecom-OS supplies
identity mapping, content, delivery intent, trace/delivery records, and an idempotency key —
it does NOT reimplement the transports. A08 owns brief content/numbers; A03 owns these ports.

Repeated delivery for the same brief/date/channel must not send twice (§12.3, §15.5). An
unmapped channel user receives no privileged identity by inference (I-09). A delivery failure
is visible and retryable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


@dataclass(frozen=True)
class MappedIdentity:
    """An Ecom-OS identity bound to a channel user (resolved, never inferred)."""

    channel: str
    external_user_id: str
    ecom_user_id: str
    access_label: str


class ChannelIdentityResolver(Protocol):
    async def resolve(
        self, channel: str, external_user_id: str
    ) -> MappedIdentity | None: ...


@dataclass(frozen=True)
class DeliveryIntent:
    """A request to deliver content through a native Hermes channel."""

    brief_id: str
    brief_date: str  # ISO date; part of the idempotency key
    channel: str
    target: str  # mapped channel destination (chat id / address)
    body_hash: str

    @property
    def idempotency_key(self) -> str:
        return f"{self.brief_id}:{self.brief_date}:{self.channel}:{self.target}"


class DeliveryStatus(str, Enum):
    delivered = "delivered"
    duplicate = "duplicate"
    failed = "failed"


@dataclass(frozen=True)
class DeliveryReceipt:
    intent: DeliveryIntent
    status: DeliveryStatus
    provider_message_id: str | None = None
    error: str | None = None

    @property
    def retryable(self) -> bool:
        return self.status is DeliveryStatus.failed


class ChannelTransport(Protocol):
    """The native Hermes messaging transport (owned by Hermes; called via the bridge)."""

    async def send(self, intent: DeliveryIntent) -> str: ...  # returns provider message id


class DeliveryLog(Protocol):
    async def get(self, idempotency_key: str) -> DeliveryReceipt | None: ...
    async def put(self, receipt: DeliveryReceipt) -> None: ...


class ScheduleSpec(Protocol):
    cron: str
    task_ref: str


@dataclass(frozen=True)
class ScheduleRef:
    schedule_id: str
    cron: str
    task_ref: str


class SchedulePort(Protocol):
    async def schedule(self, *, cron: str, task_ref: str) -> ScheduleRef: ...
    async def cancel(self, schedule_id: str) -> None: ...


# --- service ----------------------------------------------------------------
class ChannelDeliveryService:
    """Delivers content idempotently and records the receipt (Runtime §12.3)."""

    def __init__(self, transport: ChannelTransport, log: DeliveryLog) -> None:
        self._transport = transport
        self._log = log

    async def deliver(self, intent: DeliveryIntent) -> DeliveryReceipt:
        prior = await self._log.get(intent.idempotency_key)
        if prior is not None and prior.status is DeliveryStatus.delivered:
            # Already delivered for this brief/date/channel — do not send again.
            return DeliveryReceipt(
                intent=intent,
                status=DeliveryStatus.duplicate,
                provider_message_id=prior.provider_message_id,
            )
        try:
            provider_id = await self._transport.send(intent)
        except Exception as exc:  # noqa: BLE001 - surface as a visible, retryable failure
            receipt = DeliveryReceipt(
                intent=intent, status=DeliveryStatus.failed, error=str(exc)
            )
            # Not stored as delivered, so a later retry re-attempts (§15.5).
            return receipt
        receipt = DeliveryReceipt(
            intent=intent,
            status=DeliveryStatus.delivered,
            provider_message_id=provider_id,
        )
        await self._log.put(receipt)
        return receipt


# --- in-memory fakes for fixtures -------------------------------------------
class FakeChannelTransport:
    def __init__(self, *, fail_times: int = 0) -> None:
        self.sends: list[DeliveryIntent] = []
        self._fail_times = fail_times

    async def send(self, intent: DeliveryIntent) -> str:
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("channel transport unavailable")
        self.sends.append(intent)
        return f"msg_{len(self.sends)}"


class FakeDeliveryLog:
    def __init__(self) -> None:
        self._by_key: dict[str, DeliveryReceipt] = {}

    async def get(self, idempotency_key: str) -> DeliveryReceipt | None:
        return self._by_key.get(idempotency_key)

    async def put(self, receipt: DeliveryReceipt) -> None:
        self._by_key[receipt.intent.idempotency_key] = receipt


class FakeScheduler:
    def __init__(self) -> None:
        self.schedules: dict[str, ScheduleRef] = {}
        self._seq = 0

    async def schedule(self, *, cron: str, task_ref: str) -> ScheduleRef:
        self._seq += 1
        ref = ScheduleRef(schedule_id=f"sch_{self._seq}", cron=cron, task_ref=task_ref)
        self.schedules[ref.schedule_id] = ref
        return ref

    async def cancel(self, schedule_id: str) -> None:
        self.schedules.pop(schedule_id, None)


class FakeIdentityResolver:
    def __init__(self, mappings: dict[tuple[str, str], MappedIdentity]) -> None:
        self._mappings = mappings

    async def resolve(
        self, channel: str, external_user_id: str
    ) -> MappedIdentity | None:
        # Unmapped → None: no privileged identity by inference (I-09).
        return self._mappings.get((channel, external_user_id))
