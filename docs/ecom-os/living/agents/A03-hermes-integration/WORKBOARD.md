# A03 — Hermes Native Integration and Main Chat — Workboard

Slices map to Build Spec §5 (A03 owns Slice 0, Slice 3, channel transport in Slice 11).
Each item is independently verifiable.

## Implemented and verified

- **Canonical tool catalog framework** — `backend/app/tools/` (`catalog.py`, `envelope.py`,
  `generators.py`). One `ToolCatalog` generates MCP + adapter schemas (`to_mcp_tools`,
  `to_adapter_registration`) with a stable per-tool `schema_hash` + catalog
  `compatibility_hash`; read/write classification enforced; invocation/result envelopes
  (Runtime §6.2/6.3) with `validate_invocation` failing version/hash/arg mismatch before
  execution; `redact` masks declared sensitive fields. Tests: `tests/test_tool_catalog.py`
  (19 pass).
- **`HermesBridge` skeleton + capability model + probe** — `backend/app/hermes/`
  (`bridge.py` protocol, `types.py`, `capabilities.py`, `fake.py`, `probe.py`). Interactive
  create/list/resume/history/submit-stream/interrupt/branch and background
  start/stream/get/stop, behind one typed interface; `FakeHermesTransport` for fixtures;
  capability flags + `CompatibilityRecord` with feature readiness (ready/degraded/not_ready);
  fixture probe is `is_real=False` so nothing reaches `ready` without a real Hermes (I-19).
  Tests: `tests/test_hermes_bridge.py` (14 pass).
- **Tool execution + trace correlation** — `tools/invoker.py` + `trace_port.py`. `test_tool_invoker.py` (5).
- **BackgroundRunPort** — `hermes/runs.py` (durable-job + lease, poll-never-infer). `test_hermes_runs.py` (7).
- **Channel/cron delivery contracts** — `hermes/channels.py` (idempotent delivery, identity mapping, schedule). `test_hermes_channels.py` (6).
- **Conformance suite + readiness gate** — `hermes/conformance.py`. `test_hermes_conformance.py` (6).
- **Transport boundary** — `hermes/native.py` (`HermesNativeTransport`, real-Hermes blocked stub),
  `hermes/openclaw_compat.py` (`OpenClawCompatTransport`, dev/compat over OpenClaw, NOT Hermes),
  `hermes/health.py` (system-health/capability snapshot). `test_hermes_native_health.py` (7),
  `test_openclaw_compat.py` (9).
- **Catalog→MCP generation** — `mcp_server/catalog_server.py` (`build_catalog_server`).
  `test_catalog_mcp_server.py` (4).
- Pre-v2 audit complete (see `CURRENT.md`); baseline 76 A03-relevant tests pass at `3909904`.
  Total A03 v2 tests: **77** (ruff + mypy clean).

## Now (current-state model — this checkpoint)

- [x] Read full normative set + all agents' `CURRENT.md`/`INTERFACES.md` + programme state.
- [x] Audit OpenClaw gateway, `/delegate` spike, MCP server, CS runtime, frontend.
- [x] Publish living architecture, capability matrix (interfaces), risks, diagrams, baseline.
- [x] Filed decision request **DR-A03-01** + interface requests **IR-A03-01/02/03**.

## Next — Slice 0 (Contract and risk spikes) — gate before any CS automation

Ordered, each behind typed ports + fakes + conformance fixtures (no real Hermes yet → fixture-driven):

1. [x] **Capability probe + compatibility record** — `app/hermes/{capabilities,probe}.py`;
   probe writes record with required flags; missing mandatory → `not_ready`, missing optional
   → `degraded`; fixture probe never `ready`. Verified in `test_hermes_bridge.py`.
2. [x] **`HermesBridge` skeleton + interactive transport contract** — `app/hermes/bridge.py`
   + `fake.py`; create/list/resume/history/submit-stream/interrupt/branch; ordered events;
   interrupt yields `interrupted` terminal (no inferred completion). `test_hermes_bridge.py`.
   *Remaining:* real TUI Gateway JSON-RPC transport (WS/stdio) behind the same protocol.
3. [x] **Canonical tool catalog + adapter/MCP generator** — `app/tools/`; `ecom.order.get`
   defined once → adapter + MCP schema + validation + hash; unknown/stale version rejected;
   read-with-write-verb rejected. `test_tool_catalog.py`. *Remaining:* migrate the live
   `mcp_server/server.py` to source from the catalog (keep its allowlist + no-refund invariant).
4. [x] **Read-tool execution + trace correlation** — `app/tools/invoker.py` +
   `trace_port.py` (local `TracePort` + `FakeTraceSink` pending A02/IR-A03-01). `ecom.order.get`
   executes → `verified` invocation recorded, correlated to Hermes session/tool-call, sensitive
   fields redacted; schema mismatch fails before the handler runs; native non-Ecom tool call
   recorded `observed`, never `verified`. `test_tool_invoker.py` (5 pass). *Remaining:* swap the
   local port for A02's real ingest; drive a read tool through the real bridge end-to-end.
5. [x] **Background run port** — `app/hermes/runs.py` (`BackgroundRunPort` + `RunStore`/
   `LeasePort` + fakes). One run per `ecom_job_id` (idempotent, no duplicate); lease-loss
   `recover`/`start_or_recover` polls `get_run` before any new attempt; dropped stream
   recovered by status, never inferred-failed. `test_hermes_runs.py` (7). *Remaining:* bind to
   A02's real jobs/lease platform; real API-server async-run transport.
6. [x] **Native channel + cron delivery contracts** — `app/hermes/channels.py`
   (`ChannelDeliveryService`, `ChannelDeliveryPort`/`SchedulePort`, identity resolver, fakes).
   Idempotent per brief/date/channel (repeat → `duplicate`, no re-send); failure visible +
   retryable; unmapped channel user gets no privileged identity (I-09); cron schedule ref.
   `test_hermes_channels.py` (6). *Remaining:* real Hermes messaging/cron transport; A08 owns
   brief content/numbers.
7. [x] **Conformance suite + readiness gate** — `app/hermes/conformance.py`
   (`run_conformance_suite` → `ConformanceReport`). Combines protocol (§15.1) + channel (§15.5)
   + **tool-catalog (§15.2)** checks with capability negotiation; fixture/`is_real=False`,
   missing mandatory flag, or required-check failure → feature `not_ready` (§15.6); failures
   listed actionably. Tool conformance (`run_tool_conformance`: catalog discovery, adapter/MCP
   parity, unknown/stale/hash rejection, secrets-absent) is **real Ecom-OS evidence that passes
   without Hermes**. `test_hermes_conformance.py` (7).

8. [x] **Transport boundary + system-health (DR-A03-01 owner decision)** —
   `HermesNativeTransport` (real-Hermes blocked stub), `OpenClawCompatTransport` (dev/compat,
   NOT Hermes), `hermes_health_snapshot`, catalog→MCP `build_catalog_server`.
9. [x] **Conformance gate runner** — `app/hermes/conformance_cli.py` selects transport from
   env, runs the suite, emits a JSON snapshot, and exits non-zero (RED) until a real Hermes
   passes — fixtures/compat can never turn it green. `uv run python -m app.hermes.conformance_cli`
   → exit 2 BLOCKED. `test_conformance_gate.py` (7). A09 mounts it as the release gate.

## Then — Slice 3 (Hermes bridge and main chat UI) — partly BLOCKED on real Hermes

- [x] **Browser-safety boundary** — `app/hermes/chat_gateway.py` `ChatSessionGateway`:
  product-approved command allowlist only (arbitrary protocol methods like `cli.exec`/
  `config.set`/`sessions.delete`/secret/sudo refused — no proxy); profile resolved from
  authenticated identity, not browser-chosen; events sanitized of credential-like fields; no
  service credential to browser; reconnect reads real status. `test_chat_gateway.py` (7).
- [x] **Chat HTTP/SSE router** — `app/api/hermes_chat.py` exposes `/hermes/health`, session
  list/create/resume/history/status/interrupt, and `POST /sessions/{id}/messages` SSE stream of
  safe events. Injectable bridge + identity deps; transport selected from env (fixture/compat/
  native). `test_hermes_chat_api.py` (5). Needs central registration in `main.py` (IR-A03-06)
  and A01 identity→profile mapping (IR-A03-02).
- **Buildable now:** wire `HermesNativeTransport` real protocol once an endpoint exists; the
  `/hermes/health` route already serves the capability snapshot (register via IR-A03-06);
  `OpenClawCompatTransport` enables `/chat` dev against a local gateway.
- **Blocked (A03-R02):** real canonical resumed session, streamed tool events, reconnect, and
  conformance against a pinned Hermes — needs a real Hermes v0.16.0 endpoint/credentials/install.
- **Blocked on peers:** `/chat` + `/agents` UI needs A06 primitives (not_started) and the real
  bridge transport; trace-per-turn needs A02 ingest (IR-A03-01); WS auth needs A01 (IR-A03-02).

## Then — Slice 11 (channel transport)

- Channel identity/destination + cron/delivery transport contracts for A08 (A08 owns brief
  content/numbers) — contracts done in `channels.py`; real Hermes messaging/cron transport pending.

## Blocked

- **A03-R02 (hard):** real-Hermes conformance + the seven end-to-end acceptance scenarios are
  BLOCKED pending a pinned Hermes v0.16.0 endpoint/credentials/install. The fixture + compat
  transports keep all other work moving; every feature stays `not_ready` until a real probe.
- A02 trace ingest (IR-A03-01) and A01 WS identity (IR-A03-02) needed to replace local
  ports/fakes; A06 primitives needed for `/chat`/`/agents` UI. Non-blocking via fakes meanwhile.

## Exit condition

Branch ready when Runtime Spec §16 acceptance for A03 scope holds against a pinned Hermes:
canonical resumed session streamed in `/chat`; one `verified` Ecom-OS read tool + trace;
honest non-Ecom coverage; one background run; one native channel delivery; degraded-capability
behavior; conformance evidence in `/agents`/System health; no direct Hermes SQLite/profile
mutation. Build Spec Slice 0 + Slice 3 acceptance criteria pass.
