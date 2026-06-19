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
- Pre-v2 audit complete (see `CURRENT.md`); baseline 76 A03-relevant tests pass at `3909904`.
  Total A03 v2 tests: **57** (ruff + mypy clean).

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
   (`run_conformance_suite` → `ConformanceReport`). Combines protocol + channel checks with
   capability negotiation; fixture/`is_real=False`, missing mandatory flag, or required-check
   failure → feature `not_ready` (§15.6); failures listed actionably for `/agents`/System
   health. `test_hermes_conformance.py` (6).

## Then — Slice 3 (Hermes bridge and main chat UI)

- Capability/conformance UI in `/agents`; backend-managed TUI Gateway connection; `/chat`
  session list/create/resume/history; streamed messages/tool events; interrupt/reconnect;
  trace-per-turn; structured Ecom-OS tool-result cards; A06 primitives; browser receives no
  Hermes service credential.

## Then — Slice 11 (channel transport)

- Channel identity/destination + cron/delivery transport contracts for A08 (A08 owns brief
  content/numbers); real conformance delivery message.

## Blocked

- None hard-blocked. A03-R01 resolution and A02/A01 contracts are needed before marking
  features `ready`, but Slice 0 proceeds on typed ports + fakes + fixtures (Operating
  Protocol §7).

## Exit condition

Branch ready when Runtime Spec §16 acceptance for A03 scope holds against a pinned Hermes:
canonical resumed session streamed in `/chat`; one `verified` Ecom-OS read tool + trace;
honest non-Ecom coverage; one background run; one native channel delivery; degraded-capability
behavior; conformance evidence in `/agents`/System health; no direct Hermes SQLite/profile
mutation. Build Spec Slice 0 + Slice 3 acceptance criteria pass.
