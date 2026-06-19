# A03 — Hermes Native Integration and Main Chat — Current Handoff

## Safe continuation point

Branch `agent/a03-hermes-runtime` (NOT `agent/A03-hermes-integration` — do not switch),
pushed to `origin`, status `ready_for_integration` at `077109b`. Full A03 v2 foundation
landed (`app/tools/`, `app/hermes/`, `app/api/hermes_chat.py`, `app/mcp_server/catalog_server.py`,
`hermes-integration/`); isort/black/flake8/mypy --strict clean; 121 tests pass; no migrations.
The only blocker to runtime acceptance is a real Hermes endpoint (IR-A03-05). Resume by wiring
`HermesNativeTransport` against that endpoint, then registering the chat router (IR-A03-04).

## What is working

- v2: canonical tool catalog → generated MCP/adapter schemas + invocation/result envelopes
  with pre-execution validation; `HermesBridge` interactive+background contract with a fake
  transport; capability flags + probe + `CompatibilityRecord` (fixtures never reach `ready`).
- Pre-v2 baseline still live: OpenClaw WS gateway client, `/delegate` CS spike, stdio MCP
  server, CS agent-runtime loop. `mcp_server/server.py` excludes refund/cancel/void (Inv 2).

## What remains

- See `WORKBOARD.md`. Next: read-tool→trace correlation (needs IR-A03-01), durable-job/lease
  wrapper for `BackgroundRunPort`, native channel/cron spike, migrate live `mcp_server` onto
  the catalog, real TUI Gateway JSON-RPC transport, then Slice 3 `/chat` + `/agents` UI.

## Blockers and decisions

- **A03-R01** OpenClaw≡Hermes? — decision request pending; gates transport reuse.
- **A03-R02** No pinned Hermes runtime to probe — build on ports/fakes/fixtures; gate `ready`
  on real probe.
- Needs A02 trace/ingest contract and A01 WS identity contract (interface requests pending).
- See `RISKS.md` and programme decision/interface queues.

## Commands to resume

```bash
cd backend
uv sync --extra dev
uv run python -m pytest <targeted tests> -q          # NOT `uv run pytest`
uv run python -m app.hermes.conformance_cli          # conformance gate (exit 2 = BLOCKED)
```

The conformance gate is the single command that flips from BLOCKED to real evidence. To
unblock against a real Hermes (IR-A03-05), set `HERMES_NATIVE_ENDPOINT` (+ token handle) and
implement `HermesNativeTransport`'s protocol; for local dev set `HERMES_OPENCLAW_COMPAT_URL`
to use the OpenClaw compat transport. No pinned Hermes exists in this env, so all v2 work is
fixture/compat-driven and every feature stays `not_ready` (I-19).

## Do not accidentally regress

- Hermes stays an independent peer: no `state.db`/memory/profile writes; no fork/patch
  (I-01, I-04).
- Canonical transcript stays in Hermes; store only `SessionReference` + trace links (I-02).
- Do not promote the `/delegate` spike to the architecture (Common Trap #3).
- Generate adapter + MCP schemas from one canonical catalog; never hand-edit duplicates.
- `verified` coverage only for Ecom-OS-endpoint-handled invocations; native activity is
  `observed`/`unknown` (I-12).
- Browser never receives a Hermes service credential or arbitrary protocol proxy; no
  refund/cancel tool anywhere in the catalog (Invariant 2).
- Reconnect/lease-loss queries real status before retry; never infer completion (I-07/I-08).
