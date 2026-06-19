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
| New: conformance suite + readiness gate | `uv run python -m pytest tests/test_hermes_conformance.py -q` | **6 passed** | this checkpoint |
| All A03 v2 modules together | `uv run python -m pytest tests/test_tool_catalog.py tests/test_tool_invoker.py tests/test_hermes_*.py -q` | **57 passed**, 3.7s | this checkpoint |
| A03 baseline + new (regression) | `uv run python -m pytest tests/test_tool_catalog.py tests/test_hermes_bridge.py tests/test_tool_invoker.py tests/test_mcp_server.py tests/test_cs_runtime.py tests/test_cs_llm.py tests/test_gateway_*.py tests/test_session_keys.py -q` | **109 passed** baseline run; +5 invoker = **38 new** A03 v2 tests green | this checkpoint |
| Full backend suite | `uv run python -m pytest -q` (backgrounded) | exit 0 (slow integration tests near end; foreground hits 500s wall-clock) | this checkpoint |
| Static/type checks (new modules) | `uv run mypy app/tools app/hermes` | **Success: no issues** (10 files) | this checkpoint |
| Lint (new modules) | `uv run ruff check app/tools app/hermes tests/test_tool_catalog.py tests/test_hermes_bridge.py` | **All checks passed** | this checkpoint |
| Capability probe / conformance suite | fixture-level passes (`run_conformance` via `FakeHermesTransport`); real pinned-Hermes run | fixture pass; real **not run** | blocked by A03-R02 (no Hermes runtime) — fixture probe `is_real=False` so no feature `ready` |
| Trace correlation (read tool → verified invocation) | `ToolInvoker` over local `TracePort` (`test_tool_invoker.py`) | fixture pass — verified invocation + Hermes session/tool-call correlation; native call `observed` | real link pending A02 ingest (IR-A03-01) |
| Background run + reconcile | `BackgroundRunPort` over fake bridge + fake lease (`test_hermes_runs.py`) | fixture pass — idempotent (1 run/job), lease-loss polls status, dropped stream recovered | real API-server run transport + A02 jobs pending |
| Native channel/cron delivery | `ChannelDeliveryService` + fakes (`test_hermes_channels.py`) | fixture pass — delivers once, repeat→duplicate, failure retryable, unmapped→no identity, cron ref | real Hermes messaging/cron transport pending |
| Degraded capability behavior | `run_conformance_suite` readiness gate (`test_hermes_conformance.py`) | fixture pass — missing mandatory→not_ready (only that feature), missing optional→degraded | gated `not_ready` on fixtures (I-19) until real probe |
| Conformance evidence | `run_conformance_suite` → `ConformanceReport` (protocol+channel+gate) | fixture pass | real-Hermes run is the production gate (A03-R02) |
| Security/invariant checks | catalog rejects read-with-write-verb + unbound write; `validate_invocation` fails stale hash/version before execution; `redact` masks sensitive fields; `test_mcp_server.py` asserts no refund/cancel tool | pass | within the 109 above |

## Environment notes (for reproducibility)

- Backend deps install with **`uv sync --extra dev`** (the `dev` extra carries pytest).
- Run tests via **`uv run python -m pytest`**, not `uv run pytest` — the bare `pytest`
  on PATH resolves to a system interpreter without `sqlmodel`.

Replace stale results. Include exact failures; do not write "all good" without evidence.
