"""MCP server package exposing Ecom-OS read + discount tools.

Invariant 2 (hard): this server exposes ONLY read tools plus a single, capped
discount tool. There is deliberately no refund / cancel / order-write tool — the
tool list *is* the capability boundary handed to the Hermes CS subagent.
"""

from __future__ import annotations

from .server import TOOLS, build_server

__all__ = ["TOOLS", "build_server"]
