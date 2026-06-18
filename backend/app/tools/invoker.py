"""Execute a catalog tool into a traced, coverage-honest result (Runtime Spec §6.4, §7).

The invoker is the Ecom-OS-controlled endpoint: it validates against the catalog *before*
domain execution (§13.4), records a durable invocation, runs the read handler, redacts
declared sensitive fields, and returns a ``ToolResult`` linked to the trace. Because the
Ecom-OS endpoint handled it, the invocation coverage is ``verified`` (§7.2).

Business logic lives in the handlers (owned by domain agents), never here. v1 wires read
tools only; write tools route through the action contract in a later slice.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .catalog import CATALOG, Coverage, ReadOrWrite, ToolCatalog, ToolDefinition
from .envelope import (
    Freshness,
    InvocationContext,
    SchemaMismatchError,
    ToolInvocation,
    ToolResult,
    ToolStatus,
    UnknownToolError,
    redact,
    validate_invocation,
)
from .trace_port import NativeActivityRecord, ToolInvocationRecord, TracePort

# A handler receives the resolved definition, validated arguments, and context; it returns
# the raw data payload (pre-redaction).
ToolHandler = Callable[
    [ToolDefinition, dict[str, object], InvocationContext],
    Awaitable[dict[str, object]],
]


class ToolInvoker:
    def __init__(
        self,
        trace: TracePort,
        handlers: dict[str, ToolHandler],
        *,
        catalog: ToolCatalog = CATALOG,
    ) -> None:
        self._trace = trace
        self._handlers = handlers
        self._catalog = catalog

    async def _record(
        self,
        invocation: ToolInvocation,
        definition: ToolDefinition | None,
        *,
        status: ToolStatus,
        error_code: str | None = None,
    ) -> None:
        ctx = invocation.context
        await self._trace.record_tool_invocation(
            ToolInvocationRecord(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                tool_version=invocation.tool_version,
                schema_hash=invocation.schema_hash,
                coverage=Coverage.verified,  # the Ecom-OS endpoint handled this (§7.2)
                status=status.value,
                trace_id=ctx.trace_id,
                run_id=ctx.run_id,
                hermes_session_id=ctx.hermes_session_id,
                hermes_tool_call_id=ctx.hermes_tool_call_id,
                arguments_redacted=(
                    redact(definition, invocation.arguments) if definition else {}
                ),
                error_code=error_code,
            )
        )

    async def invoke(self, invocation: ToolInvocation) -> ToolResult:
        """Validate, trace, and execute one read-tool invocation."""
        # Validate before any execution. A schema/version/arg mismatch is a compatibility
        # failure recorded as a verified-but-failed invocation, never reinterpreted (§13.4).
        try:
            definition = validate_invocation(self._catalog, invocation)
        except UnknownToolError:
            await self._record(invocation, None, status=ToolStatus.failed,
                               error_code="unknown_tool")
            return ToolResult(
                ok=False, status=ToolStatus.failed,
                invocation_id=invocation.invocation_id,
                trace_id=invocation.context.trace_id,
                error={"code": "unknown_tool", "message": "tool not in catalog"},
            )
        except SchemaMismatchError as exc:
            await self._record(invocation, None, status=ToolStatus.failed,
                               error_code="schema_mismatch")
            return ToolResult(
                ok=False, status=ToolStatus.failed,
                invocation_id=invocation.invocation_id,
                trace_id=invocation.context.trace_id,
                error={"code": "schema_mismatch", "message": str(exc)},
            )

        # v1 invoker handles read tools; writes go through the action contract later.
        if definition.read_or_write is not ReadOrWrite.read:
            await self._record(invocation, definition, status=ToolStatus.failed,
                               error_code="write_not_supported")
            return ToolResult(
                ok=False, status=ToolStatus.failed,
                invocation_id=invocation.invocation_id,
                trace_id=invocation.context.trace_id,
                error={
                    "code": "write_not_supported",
                    "message": "write tools route through the action contract",
                },
            )

        handler = self._handlers.get(definition.name)
        if handler is None:
            await self._record(invocation, definition, status=ToolStatus.failed,
                               error_code="no_handler")
            return ToolResult(
                ok=False, status=ToolStatus.failed,
                invocation_id=invocation.invocation_id,
                trace_id=invocation.context.trace_id,
                error={"code": "no_handler", "message": "no handler registered"},
            )

        data = await handler(definition, invocation.arguments, invocation.context)
        safe_data = redact(definition, data)
        await self._record(invocation, definition, status=ToolStatus.completed)
        return ToolResult(
            ok=True,
            status=ToolStatus.completed,
            invocation_id=invocation.invocation_id,
            trace_id=invocation.context.trace_id,
            data=safe_data,
            freshness=Freshness(status="current"),
            coverage=Coverage.verified,
        )

    async def observe_native_tool(
        self,
        *,
        tool_name: str,
        trace_id: str | None = None,
        hermes_session_id: str | None = None,
        hermes_tool_call_id: str | None = None,
    ) -> None:
        """Record a native (non-Ecom) Hermes tool call as ``observed`` (I-12, §7.2).

        A hook seeing a terminal/browser/third-party tool call is evidence, not proof of an
        Ecom-OS operation; it is never labeled ``verified``.
        """
        await self._trace.record_native_activity(
            NativeActivityRecord(
                trace_id=trace_id,
                hermes_session_id=hermes_session_id,
                hermes_tool_call_id=hermes_tool_call_id,
                tool_name=tool_name,
                coverage=Coverage.observed,
            )
        )
