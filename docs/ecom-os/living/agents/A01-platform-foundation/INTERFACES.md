# A01 — Platform Foundation and Identity — Interfaces

Status legend: `planned` (designed, not yet coded) · `implementing` · `available`
(coded + tested on this branch). Nothing is `available` yet at 3909904.

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `ActorContext` (human/service/channel; `actor_type`, `actor_id`, roles, scopes) | v0 planned | `backend/app/auth/context.py` (to create); seam = `app/core/auth.py:AuthContext` | A02–A09 | Missing/invalid auth → `unauthenticated`; resolved server-side, never from client role names |
| `RequestContext` (`request_id`, `trace_id`, `span_id`, `parent_span_id`, actor, `store_id`, hermes ids) | v0 planned | `backend/app/core/context.py` (to create); per `03-ENGINEERING.md` §6 | A02–A09 | Absent fields stay null, never fabricated; W3C `traceparent` honoured on HTTP |
| `StoreScope` (exact `store_id`/`brand_id` binding) | v0 planned | `backend/app/core/context.py` | A04, A05, A08 | No default/latest account (AGENTS I-09); unscoped write → `forbidden`/`validation_error` |
| `Money` (integer minor units + ISO currency) | v0 planned | `backend/app/core/money.py` | A05, A08 | No float; mismatched currency → `validation_error` |
| `Uuid7` id type + generator | v0 planned | `backend/app/core/ids.py` | all | Opaque to clients; provider IDs stored separately |
| UTC datetime helpers (tz-aware) | v0 planned | `backend/app/core/time.py` (reshape `utcnow`) | all | Storage UTC; presentation tz at boundary |
| Typed `Error` envelope + code enum (15 codes, §10) | v0 planned | `backend/app/core/errors.py` + handler | all | Stable `code`, `message`, `retryable`, `trace_id`, safe `details`, optional `remediation` |
| Auth dependency / enforcement | v0 planned (facade exists) | `backend/app/api/deps.py` | all route owners | Server-side denial; 401/403 typed; frontend never authoritative |
| Owner bootstrap API (closes after first owner) | v0 planned | `backend/app/api/auth.py` (reshape `/bootstrap`) | A09 (ops), owner UI | Replayed anonymously after close → `forbidden`; reopen only via host recovery |
| Service-identity verification | v0 planned (facade `agent_auth.py`) | `backend/app/auth/service_identity.py` | A02, A03, A04 | Bad/rotated/revoked credential → `unauthenticated`; audience-scoped |
| Channel-identity lookup | v0 planned | `backend/app/auth/channel_identity.py` | A03, A05 | Unmapped sender → no privileged identity (AGENTS I-09); role re-resolved per invocation |
| Health primitives | v0 planned (stubs exist) | `backend/app/api/health.py` | A09, A07 (system) | Multi-dimension; degraded states explicit, never single green/red |
| Route-registration convention | v0 planned | doc + `app/core/router_registry.py` | A02–A09 | Domains export router + request registration; A01 registers, A09 final integration |
| Contract generation (OpenAPI→TS) | available-as-prototype | `scripts/export_openapi.py` + `frontend/orval.config.ts` → `frontend/src/api/generated` | all frontend route owners | Schema change → regenerate; breaking tool/schema change → new version, not silent edit |

## Consumes

| Interface | Owner | Required version/status | Call sites | Fallback/degraded behavior |
|---|---|---|---|---|
| Audit/trace sink (records identity/config changes) | A02 | not available | identity/config mutations | A01-owned no-op `AuditTraceSink` port + test fake until A02 ships (RISKS A01-R06) |
| UI token/component contract | A06 | not available | owner bootstrap, login, team/role routes | Use plain A06-aligned markup behind a thin wrapper until primitives land |

## Open requests

Cross-domain requests also belong in `../../00-program/INTERFACE-REQUESTS.md` (builders add
requests there; owners accept/reject in `INTERFACE-REGISTRY.md`). Planned A01 filings:

1. **To A02** — define the `AuditTraceSink` port shape A01 will call for identity/config
   audit records, and confirm A01 may ship a no-op/test fake meanwhile. Aligns with the
   A01/A02 co-owned "Trace context envelope" registry row.
2. **To A06** — request the minimal token/primitive set needed for owner bootstrap, login,
   and team/role management pages.
3. **To A09** — confirm the dependency-lock + contract-generation + migration-head workflow
   so A01's `packages/contracts` and identity migrations integrate cleanly.
4. **Decision request (A00/human)** — resolve the AGENTS.md §10 vs `03-ENGINEERING.md` §2
   repository-layout conflict before any directory moves (RISKS A01-R09).
