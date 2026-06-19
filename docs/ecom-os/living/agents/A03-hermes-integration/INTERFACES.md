# A03 — Hermes Native Integration and Main Chat — Interfaces

Status legend: `proposed` (planned, not yet coded) · `port` (typed interface + fake +
tests exist; real transport pending) · `live` (real transport, conformance-verified). No
interface is `live` yet — gated on a pinned Hermes (I-19).

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `HermesBridge` | v0 `port` | `backend/app/hermes/bridge.py` (§2.2) + `fake.py` | A05, A07, A08 | Missing mandatory capability flag → feature `not_ready`; transport loss → reconnect/poll, never infer completion |
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

## Open requests

To be filed in `../../00-program/INTERFACE-REQUESTS.md` (none filed yet this turn):

1. **A02 trace/run/tool-invocation envelope + ingest** — schema for `trace_id`, `run_id`,
   span/tool-invocation records, and the idempotent ingest endpoint, with coverage labels
   (`verified|observed|imported|unknown`). Caller A03; owner A02.
2. **A01 service identity + WS request context** — how the chat WebSocket authenticates the
   human and resolves the allowed Hermes profile; service credential scoping. Caller A03;
   owner A01.
3. **A08 metric snapshot contract** — already `proposed` in registry as A08→A03; confirm
   shape for narration request input. Caller A03; owner A08.

Cross-domain requests also appear in `../../00-program/INTERFACE-REQUESTS.md`. Do not create
a private competing contract here.
