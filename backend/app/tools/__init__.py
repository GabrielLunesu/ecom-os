"""Canonical Ecom-OS tool catalog (Runtime Spec §6).

Every Ecom-OS tool is defined ONCE here. The catalog generates the adapter
registration schema, the MCP tool schema, the server validation model, risk/autonomy
metadata, conformance fixtures, and a compatibility hash — so the adapter and MCP
surfaces can never silently diverge (AGENTS §3, RISK A03-R04).

Business logic lives in the domain handlers, never in the catalog or the thin Hermes
adapter. The catalog only describes *what a tool is*, not *how it executes*.
"""

from __future__ import annotations

from .catalog import (
    CATALOG,
    Coverage,
    ReadOrWrite,
    ReconciliationStrategy,
    RiskClass,
    ToolCatalog,
    ToolDefinition,
)
from .envelope import (
    Freshness,
    InvocationContext,
    SchemaMismatchError,
    ToolInvocation,
    ToolResult,
    ToolStatus,
    UnknownToolError,
    validate_invocation,
)
from .invoker import ToolHandler, ToolInvoker
from .trace_port import (
    FakeTraceSink,
    NativeActivityRecord,
    ToolInvocationRecord,
    TracePort,
)

__all__ = [
    "CATALOG",
    "Coverage",
    "ReadOrWrite",
    "ReconciliationStrategy",
    "RiskClass",
    "ToolCatalog",
    "ToolDefinition",
    "Freshness",
    "InvocationContext",
    "SchemaMismatchError",
    "ToolInvocation",
    "ToolResult",
    "ToolStatus",
    "UnknownToolError",
    "validate_invocation",
    "ToolHandler",
    "ToolInvoker",
    "FakeTraceSink",
    "NativeActivityRecord",
    "ToolInvocationRecord",
    "TracePort",
]
