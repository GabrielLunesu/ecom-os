# A03 — Hermes Native Integration and Main Chat — Verification

## Latest verified commit

`5f971a7` — tool catalog + HermesBridge foundation (fixture-driven). Pre-v2 baseline was
`3909904`.

## Required checks

| Check | Command/fixture | Result | Evidence |
|---|---|---|---|
| New: tool catalog + generators + envelope | `uv run python -m pytest tests/test_tool_catalog.py -q` | **19 passed** | this checkpoint |
| New: HermesBridge contract + capability probe | `uv run python -m pytest tests/test_hermes_bridge.py -q` | **14 passed** | this checkpoint |
| A03 baseline + new (regression) | `uv run python -m pytest tests/test_tool_catalog.py tests/test_hermes_bridge.py tests/test_mcp_server.py tests/test_cs_runtime.py tests/test_cs_llm.py tests/test_gateway_*.py tests/test_session_keys.py -q` | **109 passed**, 68.8s | this checkpoint |
| Full backend suite | `uv run python -m pytest -q` (backgrounded) | exit 0 (slow integration tests near end; foreground hits 500s wall-clock) | this checkpoint |
| Static/type checks (new modules) | `uv run mypy app/tools app/hermes` | **Success: no issues** (10 files) | this checkpoint |
| Lint (new modules) | `uv run ruff check app/tools app/hermes tests/test_tool_catalog.py tests/test_hermes_bridge.py` | **All checks passed** | this checkpoint |
| Capability probe / conformance suite | fixture-level passes (`run_conformance` via `FakeHermesTransport`); real pinned-Hermes run | fixture pass; real **not run** | blocked by A03-R02 (no Hermes runtime) — fixture probe `is_real=False` so no feature `ready` |
| Trace correlation (read tool → verified invocation) | pending | not run | needs A02 contract (IR-A03-01) |
| Background run + reconcile | poll-not-infer proven against fake (`test_dropped_stream_is_recovered_by_polling_not_inference`) | fixture pass | durable-job/lease wrapper pending |
| Native channel/cron delivery | pending | not run | Slice 0 item 6 |
| Security/invariant checks | catalog rejects read-with-write-verb + unbound write; `validate_invocation` fails stale hash/version before execution; `redact` masks sensitive fields; `test_mcp_server.py` asserts no refund/cancel tool | pass | within the 109 above |

## Environment notes (for reproducibility)

- Backend deps install with **`uv sync --extra dev`** (the `dev` extra carries pytest).
- Run tests via **`uv run python -m pytest`**, not `uv run pytest` — the bare `pytest`
  on PATH resolves to a system interpreter without `sqlmodel`.

Replace stale results. Include exact failures; do not write "all good" without evidence.
