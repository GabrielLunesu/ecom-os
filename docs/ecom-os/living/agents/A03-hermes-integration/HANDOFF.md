# A03 — Hermes Native Integration and Main Chat — Current Handoff

## Safe continuation point

Branch `agent/a03-hermes-runtime` (NOT `agent/A03-hermes-integration` — do not switch).
Audit + first two v2 foundation modules landed: `backend/app/tools/` (catalog) and
`backend/app/hermes/` (bridge/capabilities/fake/probe), both fixture-driven, ruff+mypy clean,
33 new tests (109 with A03 baseline). Decision/interface requests filed (DR-A03-01,
IR-A03-01..03). Resume at WORKBOARD "Next" items 4–6.

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
uv run python -m pytest <targeted tests> -q   # NOT `uv run pytest`
```

Hermes transport is unconfigured locally (`HERMES_GATEWAY_URL` unset → `/delegate` spike
falls back to direct Anthropic). Slice 0 work is fixture-driven until a pinned Hermes exists.

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
