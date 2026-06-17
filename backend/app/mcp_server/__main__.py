"""``python -m app.mcp_server`` — run the Ecom-OS MCP stdio server.

This is the launch command a Hermes ``cs`` profile points at to gain the
``mcp-ecom-os`` toolset (read + discount only — Invariant 2).
"""

from __future__ import annotations

import anyio

from app.mcp_server.server import run_stdio


def main() -> None:
    """Entrypoint: serve the MCP tools over stdio until the client disconnects."""
    anyio.run(run_stdio)


if __name__ == "__main__":
    main()
