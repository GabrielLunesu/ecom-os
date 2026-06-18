"""Tests for tool execution + trace correlation (Runtime Spec §6.4, §7.2).

Proves the acceptance-bearing behavior: an Ecom-OS read tool creates a ``verified`` traced
invocation; a stale/unknown call fails before the handler runs; a native non-Ecom tool call
is recorded ``observed`` and never ``verified`` (AGENTS I-12).
"""

from __future__ import annotations

import pytest

from app.tools.catalog import CATALOG, Coverage
from app.tools.envelope import InvocationContext, ToolInvocation, ToolStatus
from app.tools.invoker import ToolInvoker
from app.tools.trace_port import FakeTraceSink


def _order_get_invocation(**overrides: object) -> ToolInvocation:
    d = CATALOG.get("ecom.order.get")
    assert d is not None
    base = {
        "invocation_id": "inv_1",
        "tool_name": d.name,
        "tool_version": d.version,
        "schema_hash": d.schema_hash,
        "arguments": {"store_id": "st_1", "order_id": "ord_1"},
        "context": InvocationContext(
            trace_id="trc_1", hermes_session_id="hs_1", hermes_tool_call_id="tc_1"
        ),
    }
    base.update(overrides)
    return ToolInvocation(**base)  # type: ignore[arg-type]


class _Spy:
    def __init__(self) -> None:
        self.calls = 0

    async def handler(self, definition, arguments, context):  # type: ignore[no-untyped-def]
        self.calls += 1
        return {
            "order_id": arguments["order_id"],
            "found": True,
            "name": "#1001",
            "fulfillment_status": "fulfilled",
            "customer_email": "shopper@example.com",  # declared sensitive → redacted
        }


@pytest.mark.asyncio
async def test_read_tool_creates_verified_traced_invocation() -> None:
    trace = FakeTraceSink()
    spy = _Spy()
    invoker = ToolInvoker(trace, {"ecom.order.get": spy.handler})

    result = await invoker.invoke(_order_get_invocation())

    assert result.ok is True
    assert result.status is ToolStatus.completed
    assert result.coverage is Coverage.verified
    assert result.trace_id == "trc_1"
    # sensitive field redacted in the returned data
    assert result.data["customer_email"] == "[redacted]"
    assert result.data["name"] == "#1001"

    # one verified invocation recorded, correlated to the Hermes session/tool-call
    assert len(trace.invocations) == 1
    rec = trace.invocations[0]
    assert rec.coverage is Coverage.verified
    assert rec.status == ToolStatus.completed.value
    assert rec.trace_id == "trc_1"
    assert rec.hermes_session_id == "hs_1"
    assert rec.hermes_tool_call_id == "tc_1"
    # arguments recorded are redacted too (no sensitive leak into the ledger)
    assert "customer_email" not in rec.arguments_redacted  # not an input arg here


@pytest.mark.asyncio
async def test_schema_mismatch_fails_before_handler_runs() -> None:
    trace = FakeTraceSink()
    spy = _Spy()
    invoker = ToolInvoker(trace, {"ecom.order.get": spy.handler})

    result = await invoker.invoke(_order_get_invocation(schema_hash="sha256:deadbeef"))

    assert result.ok is False
    assert result.error is not None
    assert result.error["code"] == "schema_mismatch"
    assert spy.calls == 0  # handler never executed (§13.4)
    # still recorded as a verified-but-failed endpoint invocation
    assert trace.invocations[0].status == ToolStatus.failed.value


@pytest.mark.asyncio
async def test_unknown_tool_rejected() -> None:
    trace = FakeTraceSink()
    invoker = ToolInvoker(trace, {})
    result = await invoker.invoke(_order_get_invocation(tool_name="ecom.nope.get"))
    assert result.ok is False
    assert result.error is not None
    assert result.error["code"] == "unknown_tool"


@pytest.mark.asyncio
async def test_missing_handler_fails_cleanly() -> None:
    trace = FakeTraceSink()
    invoker = ToolInvoker(trace, {})  # no handler registered
    result = await invoker.invoke(_order_get_invocation())
    assert result.ok is False
    assert result.error is not None
    assert result.error["code"] == "no_handler"


@pytest.mark.asyncio
async def test_native_tool_call_is_observed_not_verified() -> None:
    trace = FakeTraceSink()
    invoker = ToolInvoker(trace, {})

    await invoker.observe_native_tool(
        tool_name="hermes.terminal.exec",
        trace_id="trc_1",
        hermes_session_id="hs_1",
        hermes_tool_call_id="tc_native",
    )

    assert len(trace.native) == 1
    assert trace.native[0].coverage is Coverage.observed
    assert trace.native[0].coverage is not Coverage.verified
    # native activity did not enter the verified invocation ledger
    assert trace.invocations == []
