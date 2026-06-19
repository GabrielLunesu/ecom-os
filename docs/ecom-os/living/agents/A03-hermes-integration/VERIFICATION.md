# A03 — Hermes Native Integration and Main Chat — Verification

## Latest verified commit

`5f971a7` — tool catalog + HermesBridge foundation (fixture-driven). Pre-v2 baseline was
`3909904`.

## Required checks

| Check | Command/fixture | Result | Evidence |
|---|---|---|---|
| New: tool catalog + generators + envelope | `uv run python -m pytest tests/test_tool_catalog.py -q` | **19 passed** | this checkpoint |
| New: HermesBridge contract + capability probe | `uv run python -m pytest tests/test_hermes_bridge.py -q` | **14 passed** | this checkpoint |
| New: tool execution + trace correlation | `uv run python -m pytest tests/test_tool_invoker.py -q` | **5 passed** | this checkpoint |
| New: BackgroundRunPort (idempotent + poll-not-infer) | `uv run python -m pytest tests/test_hermes_runs.py -q` | **7 passed** | this checkpoint |
| New: channel/cron delivery contracts | `uv run python -m pytest tests/test_hermes_channels.py -q` | **6 passed** | this checkpoint |
| New: conformance suite + readiness gate (incl. §15.2 tool conformance) | `uv run python -m pytest tests/test_hermes_conformance.py -q` | **7 passed** | this checkpoint |
| Tool-catalog conformance (§15.2, real evidence) | `app.hermes.conformance_cli` `conformance.tools` | **7/7 pass** (catalog discovery, adapter/MCP parity, unknown/stale/hash rejection, secrets absent) — real Ecom-OS evidence, Hermes-independent | n/a |
| New: transport boundary + health | `uv run python -m pytest tests/test_hermes_native_health.py -q` | **7 passed** | this checkpoint |
| New: OpenClaw compat transport | `uv run python -m pytest tests/test_openclaw_compat.py -q` | **9 passed** | this checkpoint |
| New: catalog→MCP generation | `uv run python -m pytest tests/test_catalog_mcp_server.py -q` | **4 passed** | this checkpoint |
| All A03 v2 modules together | `uv run python -m pytest tests/test_tool_catalog.py tests/test_tool_invoker.py tests/test_catalog_mcp_server.py tests/test_hermes_*.py tests/test_openclaw_compat.py -q` | **77 passed**, 2.0s | this checkpoint |
| Regression (live MCP + gateway + CS) | `uv run python -m pytest tests/test_mcp_server.py tests/test_gateway_rpc_connect_scopes.py tests/test_gateway_version_compat.py tests/test_cs_runtime.py -q` | **52 passed** | this checkpoint |
| A03 baseline + new (regression) | `uv run python -m pytest tests/test_tool_catalog.py tests/test_hermes_bridge.py tests/test_tool_invoker.py tests/test_mcp_server.py tests/test_cs_runtime.py tests/test_cs_llm.py tests/test_gateway_*.py tests/test_session_keys.py -q` | **109 passed** baseline run; +5 invoker = **38 new** A03 v2 tests green | this checkpoint |
| Full backend suite | `uv run python -m pytest -q` (backgrounded) | exit 0 (slow integration tests near end; foreground hits 500s wall-clock) | this checkpoint |
| Static/type checks (new modules) | `uv run mypy app/tools app/hermes` | **Success: no issues** (10 files) | this checkpoint |
| Lint (new modules) | `uv run ruff check app/tools app/hermes tests/test_tool_catalog.py tests/test_hermes_bridge.py` | **All checks passed** | this checkpoint |
| Capability probe / conformance suite | fixture-level passes (`run_conformance` via `FakeHermesTransport`); real pinned-Hermes run | fixture pass; real **not run** | blocked by A03-R02 (no Hermes runtime) — fixture probe `is_real=False` so no feature `ready` |
| Trace correlation (read tool → verified invocation) | `ToolInvoker` over local `TracePort` (`test_tool_invoker.py`) | fixture pass — verified invocation + Hermes session/tool-call correlation; native call `observed` | real link pending A02 ingest (IR-A03-01) |
| Background run + reconcile | `BackgroundRunPort` over fake bridge + fake lease (`test_hermes_runs.py`) | fixture pass — idempotent (1 run/job), lease-loss polls status, dropped stream recovered | real API-server run transport + A02 jobs pending |
| Native channel/cron delivery | `ChannelDeliveryService` + fakes (`test_hermes_channels.py`) | fixture pass — delivers once, repeat→duplicate, failure retryable, unmapped→no identity, cron ref | real Hermes messaging/cron transport pending |
| Degraded capability behavior | `run_conformance_suite` readiness gate (`test_hermes_conformance.py`) | fixture pass — missing mandatory→not_ready (only that feature), missing optional→degraded | gated `not_ready` on fixtures (I-19) until real probe |
| Conformance evidence + release gate | `uv run python -m app.hermes.conformance_cli` (`test_conformance_gate.py`, 7) | **exit 2 BLOCKED** on fixture — protocol checks pass but gate stays RED; no fixture can turn it green | real-Hermes run is the production gate; same command yields real evidence when IR-A03-05 lands |
| Browser protocol-safety boundary | `uv run python -m pytest tests/test_chat_gateway.py -q` | **7 passed** — off-allowlist methods denied, no profile escalation, credential fields stripped, reconnect reads status | mount behind A01-auth route (IR-A03-02/06) |
| Chat HTTP/SSE router | `uv run python -m pytest tests/test_hermes_chat_api.py -q` | **5 passed** — health reports blocked, session CRUD, SSE frames are safe events | register in `main.py` (IR-A03-06) |
| All A03 v2 modules (final) | `uv run python -m pytest tests/test_tool_catalog.py tests/test_tool_invoker.py tests/test_catalog_mcp_server.py tests/test_hermes_*.py tests/test_openclaw_compat.py tests/test_conformance_gate.py tests/test_chat_gateway.py tests/test_hermes_chat_api.py -q` | **97 passed** | this checkpoint |
| Security/invariant checks | catalog rejects read-with-write-verb + unbound write; `validate_invocation` fails stale hash/version before execution; `redact` masks sensitive fields; `test_mcp_server.py` asserts no refund/cancel tool | pass | within the 109 above |

## Environment notes (for reproducibility)

- Backend deps install with **`uv sync --extra dev`** (the `dev` extra carries pytest).
- Run tests via **`uv run python -m pytest`**, not `uv run pytest` — the bare `pytest`
  on PATH resolves to a system interpreter without `sqlmodel`.

Replace stale results. Include exact failures; do not write "all good" without evidence.
