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
- Pre-v2 audit complete (see `CURRENT.md`); baseline 76 A03-relevant tests pass at `3909904`.

## Now (current-state model — this checkpoint)

- [x] Read full normative set + all agents' `CURRENT.md`/`INTERFACES.md` + programme state.
- [x] Audit OpenClaw gateway, `/delegate` spike, MCP server, CS runtime, frontend.
- [x] Publish living architecture, capability matrix (interfaces), risks, diagrams, baseline.
- [ ] File decision request for **A03-R01 (OpenClaw≡Hermes?)** and interface requests
      (A02 trace/ingest, A01 WS identity, A08 snapshot) — `next action`.

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
4. [ ] **Read-tool-in-Hermes + trace correlation spike** → verify: one Ecom-OS read tool
   appears in a (fixtured) Hermes run, creates a `verified` invocation linked to an A02 trace;
   native non-Ecom activity labeled `observed`/`unknown`, never `verified`. (Needs IR-A03-01.)
5. [ ] **Background run port** (`BackgroundRunPort` over Hermes API-server async run) — bridge
   methods + fake done; remaining: durable-job + lease wrapper; transport timeout →
   `outcome_unknown`, reconcile via `get_run`, no duplicate run. (poll-not-infer proven in fake.)
6. [ ] **Native channel + cron delivery spike** → one test message via native Hermes channel;
   idempotent repeat; failure visible/retryable.

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
