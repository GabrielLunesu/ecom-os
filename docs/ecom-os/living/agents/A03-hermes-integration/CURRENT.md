---
owner: A03
branch: agent/a03-hermes-runtime
status: building
last_verified_commit: 5f971a7
---

# A03 — Hermes Native Integration and Main Chat — Current State

> Branch note: the goal/handoff name `agent/A03-hermes-integration`; the actual assigned
> worktree branch is `agent/a03-hermes-runtime`. Per launch instructions the branch is not
> switched. This doc tracks the real branch.

## Mission

Integrate Ecom-OS with Hermes as an independent peer using supported protocols: canonical
Hermes sessions for `/chat`, durable background runs, generated Ecom-OS tools, native
channel/cron delivery, capability negotiation, and A02 trace correlation.

## Ownership

**Owns:** `backend/app/hermes/**`, `backend/app/tools/**` canonical tool
catalog framework, `hermes-integration/**` adapter/conformance, `HermesBridge`,
`BackgroundRunPort`, capability probe/compatibility record, MCP server schema generation,
session-reference mapping, frontend `/chat` and `/agents`, channel/cron transport contracts
for A08.

**Does not own:** direct Hermes SQLite/profile mutation, operational business truth (A02),
CS policy/approvals (A05), finance calculation/brief content (A08), global UI primitives
(A06), connector business logic (A04), shared contracts/identity (A01).

## Current implementation (evidence-based audit)

The repo predates the v2 specs. It contains **two distinct gateway notions**, an MCP
server, and a CS agent-runtime loop. Classification below: `reusable`, `pattern-only`,
`obsolete-as-architecture`.

### 1. OpenClaw gateway client — `backend/app/services/openclaw/` (~7,103 LOC, 26 files)

A complete, working integration with an external **OpenClaw agent gateway** over
**WebSocket JSON-RPC** (`{"type":"req|res|event"}`, `PROTOCOL_VERSION = 3`), with Ed25519
device-pairing auth and CalVer version pinning.

- Transport core: `gateway_rpc.py` — `openclaw_call(method, params, *, config)`,
  ~110 RPC verbs in `GATEWAY_METHODS` (incl. `chat.send`, `chat.history`, `chat.abort`,
  `sessions.list/preview/patch/reset/delete/compact`, `agent`, `agent.wait`, `cron.*`,
  `config.*`, `exec.approval.*`, `node.pair.*`, `device.pair.*`). `GatewayConfig` frozen
  dataclass. `connect` handshake pins `minProtocol/maxProtocol=3` + optional
  `connect.challenge` nonce.
- Version pin: `gateway_compat.py` — `check_gateway_version_compatibility` (CalVer vs
  `settings.gateway_min_version="2026.02.9"`).
- Device identity: `device_identity.py` — Ed25519 identity at
  `~/.openclaw/identity/device.json` (env `OPENCLAW_GATEWAY_DEVICE_IDENTITY_PATH`).
- Read APIs: `session_service.py` (`sessions.list`, history, send, status+version check),
  surfaced by `backend/app/api/gateway.py` (`/gateways/status|sessions|...|/commands`).
- Lifecycle/provisioning: `provisioning.py` (DB-free control plane, `GatewayControlPlane`
  ABC at `provisioning.py:501`), `provisioning_db.py` (agent lifecycle CRUD + SSE
  `stream_agents`), `lifecycle_*` (RQ reconcile), `admin_service.py`, `coordination_service.py`.
- Clean seams: `GatewayControlPlane` ABC + `GatewayConfig` + `internal/retry.py` +
  `internal/session_keys.py` + `policies.py` are protocol-agnostic.

**Classification:** `pattern-only`. OpenClaw protocol v3 is a **different product/protocol**
than the spec's pinned Hermes (`v0.16.0` / `v2026.6.5`, NousResearch TUI Gateway JSON-RPC).
Its envelope handling, version-pin, retry, session-key, and `GatewayControlPlane` seam are
strong reuse references for `HermesBridge`, but the wire methods, device-pairing, and
provisioning control-plane are not the v2 Hermes contract. **Open question A03-R01: is
"OpenClaw" the prior name of "Hermes"?** (DB is named `openclaw_agency`.) Resolution gates
how much transport code is reused vs newly written. See `RISKS.md` + decision request.

### 2. Hermes `/delegate` HTTP spike — `agent_runtime/hermes.py` (86 LOC), `cs_llm.py`

`HermesRuntime(LLMCSRuntime)` overrides only `_create_message`: when `HERMES_GATEWAY_URL`
is set it POSTs an Anthropic-Messages-shaped body (`profile="cs"`, system, tools, messages)
to `{HERMES_GATEWAY_URL}/delegate` with `Authorization: Bearer HERMES_API_KEY`; otherwise
falls back to direct Anthropic. `cs_llm.py:110` does the same for email generation.

**Classification:** `obsolete-as-architecture` (Common Trap #3). `/delegate` is a
hypothetical single-shot HTTP endpoint, not a validated Hermes protocol (no sessions, no
streaming, no history, no interrupt, no run lifecycle). Useful only as a degraded
"no native Hermes" fallback concept. The v2 `HermesBridge` replaces it.

### 3. MCP server — `backend/app/mcp_server/server.py` (303 LOC)

stdio MCP server `mcp-ecom-os` exposing **7 hand-written tools** (`get_shop_info`,
`lookup_order`, `get_fulfillments`, `search_vault`, `list_open_tickets`, `get_ticket`,
`create_discount` capped at 20%). Injectable session/shopify factories; hermetic tests.

**Classification:** `reusable` foundation, but tool list is **hand-maintained**, violating
"generate adapter+MCP schemas from one canonical catalog" (Runtime Spec §6.1). Becomes the
MCP-emit target of the new catalog generator; tools migrate to catalog definitions with
required metadata (version, schema_hash, risk_class, coverage, etc.).

### 4. CS agent-runtime loop — `agent_runtime/{base,llm,in_app,flow,wismo}.py`

`AgentRuntime.handle_ticket` contract; `LLMCSRuntime` runs an 8-turn Anthropic tool-use
loop with inline `TOOLS` (`llm.py:78`); `InAppCSRuntime`/`FlowCSRuntime` deterministic.
`cs_loop._select_runtime` switches on env `CS_RUNTIME` (`""|llm|hermes|flow`).

**Classification:** ticket handling is **A05's domain**, not A03. The reusable A03 piece is
the *background-run* shape: a durable job selects a runtime and drives a bounded tool loop.
v2 reframes this as `BackgroundRunPort` over Hermes API-server async runs, with tools from
the catalog rather than inline schemas. A03 provides the port; A05 owns ticket workflow.

### 5. Frontend — `frontend/src/app/(ecom)/{chat,agents}/page.tsx`

`(ecom)/chat` posts to mock `/api/v1/ecom/chat` (request/response, no streaming).
`(ecom)/agents` edits mock agent templates. Generated gateway-session API hooks
(`listGatewaySessions...`, `getSessionHistory...`, `sendGatewaySessionMessage...`) exist
but have **zero UI consumers**. SSE streaming pattern (fetch + ReadableStream + backoff) is
proven in `boards/[boardId]/page.tsx:1852` and `activity/page.tsx`. Orval codegen + auth
mutator + design primitives (`components/ui/`) present.

**Classification:** chat/agents pages are `obsolete-as-architecture` mock scaffolds; rebuilt
on the real Hermes-session transport using A06 primitives and the proven SSE pattern.

## Implemented v2 (committed at `5f971a7`)

All pure-Python, no DB migration, fixture-driven (Operating Protocol §7); ruff + mypy clean;
97 new tests pass. Per the owner decision on DR-A03-01, OpenClaw is a dev/compat transport
only and `HermesNativeTransport` is the real-Hermes seam. Real-Hermes conformance is BLOCKED
(A03-R02); A01 WS identity and A02 ingest are the remaining seams to swap fakes for
(IR-A03-01/02). Until a release is pinned, every feature is gated `not_ready` (I-19).

- **`backend/app/tools/`** — canonical tool catalog (`catalog.py`: `ToolDefinition` with all
  §6.1 metadata + `schema_hash`; `ToolCatalog` + `compatibility_hash`; seeded read tools
  `ecom.store.get`/`order.get`/`order.search`/`trace.search`). `envelope.py`:
  `InvocationContext`/`ToolInvocation`/`ToolResult` (§6.2/6.3) + `validate_invocation`
  (rejects unknown tool, stale version, hash mismatch, bad args **before** execution, §13.4)
  + `redact`. `generators.py`: `to_mcp_tools` / `to_adapter_registration` / `catalog_manifest`
  from the one catalog. Read-tool-that-writes and unbound/unreconcilable write are rejected at
  definition time. `invoker.py` + `trace_port.py`: `ToolInvoker` validates → records a
  `verified` invocation via a local `TracePort` (`FakeTraceSink`, pending A02/IR-A03-01) →
  executes the read handler → redacts → returns a trace-linked `ToolResult`; native non-Ecom
  tool calls recorded `observed`, never `verified` (I-12). Tests `tests/test_tool_catalog.py`,
  `tests/test_tool_invoker.py`.
- **`backend/app/hermes/`** — `bridge.py` (`HermesBridge` Protocol, §2.2); `types.py` (typed
  refs/events); `capabilities.py` (flags §3.2, `FEATURE_REQUIREMENTS`, `CompatibilityRecord`,
  `evaluate_feature`); `fake.py` (`FakeHermesTransport` in-memory fixture); `probe.py`
  (`capability_probe` + `run_conformance`, §3.1/§15.1). `is_real=False` on fixtures keeps
  every feature `not_ready` until a real Hermes is pinned (I-19). Tests
  `tests/test_hermes_bridge.py`.

- **`backend/app/hermes/runs.py`** — `BackgroundRunPort` over the bridge: one run per
  `ecom_job_id` (idempotent, I-07); lease-loss `recover`/`start_or_recover` polls `get_run`
  before any new attempt (never infer failure, I-08/§5.3); typed `RunStore`/`LeasePort` + fakes
  pending A02. Tests `tests/test_hermes_runs.py`.
- **`backend/app/hermes/channels.py`** — `ChannelDeliveryService` + `ChannelDeliveryPort`/
  `SchedulePort` + identity resolver (Runtime §12, I-17). Idempotent per brief/date/channel
  (repeat → `duplicate`); failure visible + retryable; unmapped channel user → no privileged
  identity (I-09). Tests `tests/test_hermes_channels.py`.
- **`backend/app/hermes/conformance.py`** — `run_conformance_suite` → `ConformanceReport`
  combining protocol + channel checks with capability negotiation; fixture/missing-mandatory/
  failed-check → feature `not_ready` (§15.6); actionable failures for `/agents`/System health.
  Tests `tests/test_hermes_conformance.py`.

- **Transport boundary (DR-A03-01 resolved):** `hermes/native.py` `HermesNativeTransport` is
  the real pinned-Hermes seam — an honest **blocked stub** (reports blocked health, refuses
  ops) until a real Hermes v0.16.0 endpoint is provided; it must never be satisfied by OpenClaw.
  `hermes/openclaw_compat.py` `OpenClawCompatTransport` adapts the in-repo OpenClaw WS gateway
  (`sessions.patch`/`chat.history`/`chat.send`/`chat.abort`) to the bridge **for local dev
  only**, clearly labeled "NOT real Hermes" with degraded (non-streaming) `submit_prompt` and
  unsupported background/branch. Tests `tests/test_hermes_native_health.py`,
  `tests/test_openclaw_compat.py`.
- **`hermes/health.py`** — `hermes_health_snapshot` assembles the compatibility/conformance/
  readiness view for `/system` + `/agents`, reporting `conformance_blocked` on fixtures and the
  native stub (real conformance BLOCKED, never faked). A09 mounts the route (IR pending).
- **`mcp_server/catalog_server.py`** — `build_catalog_server`/`build_catalog_handlers` generate
  a real MCP server from the catalog with per-call validation. The live `mcp_server/server.py`
  (A05-owned CS tool names) is unchanged; it migrates once A05 registers its tools into the
  catalog (registration contract). Tests `tests/test_catalog_mcp_server.py`.
- **`hermes/chat_gateway.py`** — `ChatSessionGateway`: the browser-facing protocol safety
  boundary (Runtime §4.1). Only product-approved commands; arbitrary protocol methods
  (`cli.exec`/`config.set`/`sessions.delete`/secret/sudo) refused — no proxy; profile resolved
  from authenticated identity (no browser escalation, I-09); events sanitized of credential
  fields; reconnect reads real status (I-08). Tests `tests/test_chat_gateway.py`.
- **`hermes/conformance_cli.py`** — `run_conformance_gate`/`evaluate_gate`: transport-selecting
  release gate; RED (exit ≠ 0) until a real Hermes passes; fixtures/compat can never turn it
  green. `uv run python -m app.hermes.conformance_cli` → exit 2 BLOCKED. Tests
  `tests/test_conformance_gate.py`.
- **`api/hermes_chat.py`** — HTTP/SSE router (`/hermes/health`, session
  list/create/resume/history/status/interrupt, SSE `messages`). Browser reaches only
  allowlisted ops via `ChatSessionGateway`; no credential forwarded; profile bound to identity.
  Transport selected from env. Exports `router` only; central registration is A01/A09 (IR-A03-06).
  Tests `tests/test_hermes_chat_api.py`.

These supersede the `/delegate` spike as the architecture. **Real-Hermes conformance is BLOCKED
(A03-R02)** pending a pinned endpoint; the bridge runs on fixtures (and optionally OpenClaw
compat) until then.

## Target architecture

See `DIAGRAMS.md`. Core: `HermesBridge` (Runtime Spec §2.2) normalizes two supported
transports — **interactive** (TUI Gateway JSON-RPC over backend-controlled WS/stdio) and
**background** (Hermes API-server async runs) — behind one typed interface. A capability
probe writes a visible compatibility record; each feature declares required flags and
degrades only itself. One canonical tool catalog generates adapter schema, MCP schema,
server validation, risk metadata, and conformance fixtures. Every Ecom-OS tool invocation
and every chat turn links to an A02 trace with honest coverage labels.

## Dependencies

- **Consumes:** A01 service/channel identity + request context; A02 trace/run/tool-invocation/
  action ledger + ingest endpoint; A06 UI primitives/shell; A08 metric snapshot for brief.
- **Exposes:** `HermesBridge`, `BackgroundRunPort`, `SessionReference`, capability flags,
  tool transport/generator, narration request, `ChannelDeliveryPort`, `SchedulePort` —
  consumed by A05 (CS runs), A07 (workspace), A08 (brief delivery), A09 (integration/health).

## Status

Audit complete; no v2 code written yet. Baseline: 76 A03-relevant tests pass at
`3909904` (see `VERIFICATION.md`). Next: resolve A03-R01, publish interface requests, then
Slice 0 spikes (capability probe + bridge skeleton + read-tool-in-Hermes + trace link).
