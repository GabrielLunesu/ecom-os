# A03 — Hermes Native Integration and Main Chat — Interfaces

Status legend: `proposed` (planned, not yet coded) · `port` (typed interface + fake +
tests exist; real transport pending) · `live` (real transport, conformance-verified). No
interface is `live` yet — gated on a pinned Hermes (I-19).

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `HermesBridge` | v0 `port` | `backend/app/hermes/bridge.py` (§2.2); transports `fake.py`, `native.py` (real, **blocked stub**), `openclaw_compat.py` (dev/compat, NOT Hermes) | A05, A07, A08 | Missing mandatory capability flag → feature `not_ready`; native transport BLOCKED until real endpoint (A03-R02); transport loss → reconnect/poll, never infer completion |
| Hermes system-health snapshot | v0 `port` | `backend/app/hermes/health.py` `hermes_health_snapshot` | A09 (`/system`), A03 (`/agents`) | `conformance_blocked: true` on fixtures/native stub; real conformance never faked |
| Catalog→MCP server generator | v1 `port` | `backend/app/mcp_server/catalog_server.py` | Hermes MCP config; A05 registers CS tool defs | Handler outside catalog rejected; per-call arg validation before dispatch |
| `BackgroundRunPort` | v0 `port` | `backend/app/hermes/runs.py` (+ `RunStore`/`LeasePort`) | A05 (ticket runs), A08 (brief narration) | Idempotent per `ecom_job_id`; lease-loss polls `get_run` before any new attempt; HTTP timeout ≠ failure → reconcile, no duplicate |
| `ChannelDeliveryPort` + `SchedulePort` | v0 `port` | `backend/app/hermes/channels.py` | A08 (brief/alert delivery) | Idempotent per brief/date/channel (repeat → `duplicate`); failure visible+retryable; unmapped channel user → no privileged identity (I-09) |
| Conformance suite + readiness gate | v0 `port` | `backend/app/hermes/conformance.py` | A09 (System health), A03 `/agents` | Required-check failure / missing mandatory flag / fixture → feature `not_ready` (§15.6) |
| `SessionReference` | v0 `port` | `backend/app/hermes/types.py` `HermesSessionRef` (§4.3) | A02, A05, A07 | Stores refs + derived metadata only; never canonical transcript; history declares source |
| Capability flags + compatibility record | v0 `port` | `backend/app/hermes/capabilities.py` + `probe.py` (§3.1/§3.2) | A09 (System health), all feature owners | Probe failure / fixture → dependent feature `not_ready`, visible in `/system` |
| Tool catalog + generator | v1 `port` | `backend/app/tools/{catalog,envelope,generators}.py` (§6.1) | A04/A05/A07/A08 register tool defs; A03 emits adapter+MCP schema | Schema-hash/version/arg mismatch fails before domain execution (§13.4) |
| MCP server (generated) | v1 live (hand-written), `proposed` regen onto catalog | `backend/app/mcp_server/server.py`; target: `generators.to_mcp_tools` | Hermes MCP config (allowlist) | Discovery ≠ authorization; unknown tool version rejected |
| Narration request | v0 `proposed` | `backend/app/hermes/narration.py` | A08 daily brief | Hermes/model down → deterministic fallback; narration never computes numbers |
| `ChannelDeliveryPort` | v0 `proposed` | `backend/app/hermes/channels.py` (Runtime Spec §12) | A08 (brief/alert delivery) | Identity unmapped → no privileged identity; delivery intent + idempotency key |
| `SchedulePort` (cron) | v0 `proposed` | `backend/app/hermes/schedule.py` (Runtime Spec §12.3) | A08 | Missing `cron.scheduling` flag degrades scheduled delivery only |
| Chat protocol-safety gateway | v0 `port` | `backend/app/hermes/chat_gateway.py` `ChatSessionGateway` | mounted by `api/hermes_chat.py` | Off-allowlist command → `BrowserCommandDenied`; no profile escalation; no credential to browser; reconnect reads status |
| Chat HTTP/SSE router (`/hermes/*`) | v0 `port` | `backend/app/api/hermes_chat.py` `router` | browser `/chat`; A01/A09 register in `main.py` (IR-A03-06) | Only allowlisted ops exposed; `/hermes/health` reports `conformance_blocked` honestly; SSE frames sanitized |
| Conformance gate runner | v0 `port` | `backend/app/hermes/conformance_cli.py` | A09 release gate / CI | Exit ≠ 0 (RED) until a real Hermes passes; fixtures never green |
| `/chat`, `/agents` routes | `proposed` | `frontend/src/app/chat`, `/agents` | operators | Loading/empty/stale/unavailable/permission/error + reconnect states |

## Consumes

| Interface | Owner | Required version/status | Call sites (planned) | Fallback/degraded behavior |
|---|---|---|---|---|
| Trace context envelope (`trace_id`/`run_id`/spans) | A01/A02 | needed for Slice 0 read-tool link | tool handlers, chat-turn lifecycle | Local typed port/fake until A02 ledger lands; reconcile later |
| Durable action port | A02 | needed for write tools (later slice) | catalog write-tool handlers | Read-only tools first; write tools gated on action ledger |
| Trace ingest endpoint (idempotent inbox) | A02 | needed for observer telemetry | adapter/hook telemetry forwarder | Buffer bounded; duplicates idempotently ignored |
| Service/channel identity + request context | A01 | needed for auth/scope on bridge + tools | WS auth, tool context resolution | Local fake identity in fixtures; no privileged default identity |
| UI primitives / shell / command palette | A06 | needed for `/chat`, `/agents` | chat + agents pages | Build behind A06 tokens; do not fork design system |
| Metric snapshot contract | A08 | needed for brief narration | narration request | Deterministic snapshot is source; narration optional |

## Open cross-domain requests (A03-owned record)

Per integration protocol, A03 records its cross-domain needs here; `00-program/**` is
A00-owned and is not edited by builders. Owners/A00 transcribe accepted entries into the
registry.

| ID | Owner | Need | Proposed shape / link | Blocking |
|---|---|---|---|---|
| IR-A03-01 | A02 | Trace/run/tool-invocation envelope + idempotent ingest with coverage labels (`verified`/`observed`/`imported`/`unknown`) | Runtime §6.2/§7; replaces local `tools/trace_port.py` | verified trace links for read tools/runs |
| IR-A03-02 | A01 | Service/channel identity + WS request context; identity→Hermes-profile mapping; service-credential scoping | Runtime §4.1/§14; replaces `hermes_chat.get_chat_identity` placeholder | authenticated `/chat`, exact tool identity |
| IR-A03-03 | A08 | Confirm metric snapshot contract shape consumed by brief narration | Registry "Metric snapshot contract" (A08→A03); Runtime §12.2 | brief narration (non-blocking now) |
| IR-A03-04 | A09/A01 | Register `app/api/hermes_chat.py` `router` (`/hermes`) in `app/main.py` | this `INTERFACES.md`; Build Spec Slice 3 | `/hermes/*` reachable |
| IR-A03-05 | infra/human | Provide a pinned **real Hermes v0.16.0** endpoint + credentials/install target | DR-A03-01; `HermesNativeTransport`; A03-R02 | real conformance + all 7 acceptance scenarios |

## Decision record (A03-owned)

- **DR-A03-01 — OpenClaw is NOT Hermes (owner-decided).** The in-repo OpenClaw gateway is a
  legacy/compat transport only (`hermes/openclaw_compat.py`); the real-Hermes seam is
  `HermesNativeTransport`. Real-Hermes conformance stays BLOCKED, not faked, until IR-A03-05.

A03 does not edit `00-program/**`; these are surfaced for A00/owners to transcribe into the
registry. A03 does not create a competing private contract.
