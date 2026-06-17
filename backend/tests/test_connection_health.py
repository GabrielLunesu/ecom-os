"""Tests for the §1.5 bootstrap gate: refuse the CS loop until both live."""

from __future__ import annotations

import pytest

from app.services import connection_health as ch
from app.services.connection_health import (
    CSLoopNotReady,
    ProviderHealth,
    assert_ready_for_cs_loop,
    connections_status,
)


@pytest.fixture
def both_up(monkeypatch: pytest.MonkeyPatch) -> None:
    async def shop() -> ProviderHealth:
        return ProviderHealth("shopify", True, "connected: CHICAGO OUTLET")

    async def inbox() -> ProviderHealth:
        return ProviderHealth("inbox", True, "outlook: ACTIVE")

    monkeypatch.setattr(ch, "check_shopify", shop)
    monkeypatch.setattr(ch, "check_inbox", inbox)


@pytest.fixture
def inbox_down(monkeypatch: pytest.MonkeyPatch) -> None:
    async def shop() -> ProviderHealth:
        return ProviderHealth("shopify", True, "connected: CHICAGO OUTLET")

    async def inbox() -> ProviderHealth:
        return ProviderHealth("inbox", False, "no active mail account")

    monkeypatch.setattr(ch, "check_shopify", shop)
    monkeypatch.setattr(ch, "check_inbox", inbox)


@pytest.mark.asyncio
async def test_status_ready_when_both_up(both_up: None) -> None:
    status = await connections_status()
    assert status["ready"] is True
    await assert_ready_for_cs_loop()  # does not raise


@pytest.mark.asyncio
async def test_gate_blocks_when_inbox_down(inbox_down: None) -> None:
    status = await connections_status()
    assert status["ready"] is False
    with pytest.raises(CSLoopNotReady, match="inbox"):
        await assert_ready_for_cs_loop()


@pytest.mark.asyncio
async def test_status_payload_carries_no_secret(both_up: None) -> None:
    import json

    dumped = json.dumps(await connections_status())
    for marker in ("shpat_", "Bearer", "x-api-key", "access_token"):
        assert marker not in dumped
