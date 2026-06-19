# A01 — Platform Foundation and Identity — Interfaces

Status legend: `planned` · `implementing` · `available` (coded + tested at `f92adbb`).

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `ActorContext` (human/service/channel; `actor_type`, `actor_id`, roles, scopes) | v1 available | `app/core/context.py`; resolver `app/auth/actor.py` | A02–A09 | Missing/invalid auth → `unauthenticated`; resolved server-side, never from client role names |
| `RequestContext` (`request_id`, `trace_id`, `span_id`, `parent_span_id`, actor, `store_id`, hermes ids) | v1 available | `app/core/context.py`; dep `app/auth/context.py:get_request_context` | A02–A09 | Absent fields stay null, never fabricated; W3C `traceparent` honoured on HTTP |
| `StoreScope` (exact `store_id`/`brand_id` binding) | v1 available | `app/core/context.py` | A04, A05, A08 | No default/latest account (I-09); unscoped write → `forbidden`/`validation_error` |
| `Money` (integer minor units + ISO currency) | v1 available | `app/core/money.py` | A05, A08 | No float; mismatched currency → `CurrencyMismatchError`/`validation_error` |
| `uuid7()` sortable id generator | v1 available | `app/core/ids.py` | all | Opaque to clients; provider IDs stored separately |
| tz-aware UTC helpers | v1 available | `app/core/time.py:{now_utc,ensure_utc,to_timezone}` | all | Storage UTC; presentation tz at boundary; legacy `utcnow` (naive) retained |
| Typed `ErrorEnvelope` + `ErrorCode` (15 codes) + `ApiError` | v1 available | `app/core/errors.py`; handler `app/core/error_handling.py` | all | Stable `code`/`detail`/`retryable`/`trace_id`/safe `details`/`remediation`; details redacted |
| Permission/role enforcement deps | v1 available | `app/auth/actor.py:{require_permission,require_role,get_actor_context}` | all route owners | Server-side `forbidden`; frontend never authoritative |
| Owner bootstrap API (closes after first owner) | v1 available | `app/auth/bootstrap.py`; `app/api/identity.py` | A09 (ops), owner UI | Anonymous → 401; non-owner after close → `forbidden`; reopen only via host `reopen_bootstrap` |
| Service-identity verification | v1 available | `app/auth/service_identity.py` (+ `service_tokens.py`) | A02, A03, A04 | Bad/rotated/revoked token → `None`; O(1) selector lookup; audience-scoped |
| Channel-identity lookup + actor resolution | v1 available | `app/auth/channel_identity.py` | A03, A05 | Unmapped sender → no identity (I-09); role re-resolved per invocation |
| Health primitives + readiness report | v1 available | `app/core/health.py`; `/readyz`, `/readyz/details` | A09, A07 (system) | Multi-dimension; `down`→503; other domains' dims = `unknown` until wired |
| Route-registration convention | v1 available | `app/api/registry.py:{DOMAIN_ROUTERS,register_domain_routers}` | A02–A09 | Domains export router + request a one-line entry; A01 registers, A09 final integration |
| Identity fixtures | v1 available | `app/auth/fixtures.py:seed_identity_fixtures` | all (tests) | Deterministic owner/admin/viewer + service + channel + unmapped sender |
| Contract generation (OpenAPI→TS) | v1 available | `backend/scripts/export_openapi.py` + `frontend/orval.config.ts` → `frontend/src/api/generated` | all frontend route owners | Schema change → regenerate; breaking change → new version, not silent edit |
| `AuditTraceSink` port (A01 exposes the port; A02 implements) | v1 available (no-op) | `app/auth/audit.py:{AuditTraceSink,get_audit_sink,set_audit_sink}` | A02 (provider), A01 (caller) | Default no-op logs honestly; A02 injects durable sink |

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
