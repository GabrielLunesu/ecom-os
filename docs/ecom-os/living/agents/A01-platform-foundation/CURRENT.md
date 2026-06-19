---
owner: A01
branch: agent/a01-foundation
status: ready_for_integration
last_verified_commit: 4b214ee
---

# A01 — Platform Foundation and Identity — Current State

## Mission

Establish the shared production skeleton, identity model, request/actor/store/trace
context, common ID/time/money/error types, typed API errors, auth enforcement, health
primitives, shared contract generation, route-registration conventions, and migration
conventions that every domain (A02–A09) builds on. Preserve useful prototype behaviour and
move it behind v2 contracts; no big-bang folder rewrite.

## Ownership

**Owns:** `backend/app/auth/**` (to be created), `backend/app/core/**` shared primitives,
owner/bootstrap APIs + UI, users/roles/role-permissions, service identities, channel
identity records, common UUID/time/money/error types, request/actor/store/trace context,
central API router registration (`backend/app/main.py`), `packages/contracts/` (generated
contracts) — currently realised as the `openapi.json` → orval → `frontend/src/api/generated`
pipeline, backend dependency/lock files (`backend/pyproject.toml`, `backend/uv.lock`),
identity migrations, and shared fixtures. Frontend routes: owner bootstrap, login,
team/role management.

**Does not own:** durable event/action/trace/job internals (A02), Hermes transport/tooling
(A03), connectors/commerce sync (A04), CS/grants/policies/approvals (A05), UI primitives /
global shell (A06), Today/tasks/knowledge (A07), metrics/finance/brief (A08), deployment
topology / compose / CI / migration-merge revisions (A09).

## Repository context

The backend is a fork of **`openclaw-mission-control`** (board/agent orchestration), with an
Ecom-OS layer (brands, stores, Shopify connectors, CS tickets, refunds) bolted on. The
package is still named `openclaw-agency-backend` and the app titled "Mission Control API"
(`backend/app/main.py:468`). Layout is `backend/app/{api,core,db,models,schemas,services}`
(SQLModel-based), **not** the `backend/{api,domain,application,infrastructure,workers}` tree
in AGENTS.md §10. The AGENTS.md §10 vs `03-ENGINEERING.md` §2 layout conflict is logged as
a decision request (see RISKS A01-R09); A01 will not force a rename — it adds `app/auth/`
and consolidates shared primitives into `app/core/` behind stable seams.

## Implemented by A01 (at f92adbb)

Eight tested vertical slices on top of the audited prototype. All A01 code passes
`ruff`, `mypy --strict` (211 files), and its unit/integration suites (see VERIFICATION).

| # | Capability | Code | Tests |
|---|---|---|---|
| 1 | Common types: UUIDv7, Money(minor units+ISO, no float), tz-aware time | `app/core/ids.py`, `money.py`, `time.py` | `tests/test_foundation_types.py` |
| 1 | Typed error envelope + 15 normative codes; `ApiError` handler | `app/core/errors.py`, `error_handling.py` | `test_foundation_types.py` |
| 2 | RequestContext/ActorContext/StoreScope + W3C trace propagation | `app/core/context.py`, `app/auth/context.py`, `error_handling.py` | `test_request_context.py` |
| 3 | Identity schema (roles/permissions/service+channel identities/bootstrap) + migration | `app/models/identity.py`, `migrations/versions/a01_0001_identity_foundation.py` | `test_identity_migration.py` |
| 4 | Owner bootstrap that closes; role seeding; audit-sink port; `/identity/*` | `app/auth/bootstrap.py`, `roles.py`, `actor.py`, `audit.py`, `app/api/identity.py` | `test_owner_bootstrap.py` |
| 5 | Service & channel identity verification; role enforcement; fixtures | `app/auth/service_identity.py`, `channel_identity.py`, `fixtures.py`, `service_tokens.py` | `test_identity_enforcement.py` |
| 6 | Health primitives + multi-dimension readiness (`/readyz`, `/readyz/details`) | `app/core/health.py`, `app/main.py` | `test_health_primitives.py` |
| 7 | Route-registration convention; regenerated strict TS client | `app/api/registry.py`, `frontend/src/api/generated/**` | `test_contract_and_registry.py` |
| 8 | Secret redaction at log + error boundaries; detection corpus | `app/core/redaction.py`, `logging.py`, `error_handling.py` | `test_secret_redaction.py` |

Consumed-port: A02 audit/trace sink via `app/auth/audit.py` (no-op default + in-memory
fake) until A02 ships. Local auth remains the explicit dev/self-hosted mode.

## Prototype baseline (audited at 3909904)

Status legend: **[reuse]** keep as-is · **[facade]** keep the seam, reshape behind it ·
**[build]** absent, A01 must create · **[liability]** present but violates a v2 invariant.
Items marked [build]/[liability] below that A01 has since resolved are noted in the
"Implemented by A01" table above; the rest remain as the prototype's current state.

### Identity & auth
- **[facade]** Auth seam: `app/core/auth.py` (`get_auth_context`, `AuthContext`) and
  `app/api/deps.py` (`require_user_auth`, `require_user_or_agent`, `require_org_member`,
  `require_org_admin`). Every router depends on these — they are the universal enforcement
  point to reshape behind.
- **[facade]** Two auth modes via `AuthMode` enum (`app/core/auth_mode.py`): `clerk`
  (validates Clerk session JWT, upserts local `User`) and `local` (single shared static
  bearer token `settings.local_auth_token`, mapped to one synthetic user). Local mode is
  the seam for a real dev/self-hosted local-auth mode.
- **[facade]** Service identity: `app/core/agent_auth.py` + `app/core/agent_tokens.py` —
  opaque `secrets.token_urlsafe(32)` tokens, PBKDF2-HMAC-SHA256 (200k) hashed into
  `Agent.agent_token_hash`. Sound hashing primitive; lookup is O(n) (RISKS A01-R07).
- **[liability]** Owner bootstrap does not exist as an explicit closing flow.
  `ensure_member_for_user` (`app/services/organizations.py:276`) silently makes every new
  user `owner` of an auto-created "Personal" org. No single-owner gate, no close-after-first.
- **[build]** No `Role`/`Permission`/`role_permissions` tables — RBAC is hardcoded role
  strings (`OrganizationMember.role` ∈ {member,admin,owner}) + per-board booleans.
- **[build]** No `channel_identities` table/lookup. No human password auth (no hash, no
  login/logout, no session/refresh issuance) in local mode.

### Common types
- **[reuse]** `app/core/time.py:utcnow()` — but returns **naive** UTC (RISKS A01-R03).
- **[liability]** IDs: every model uses `uuid4` in Python (`Field(default_factory=uuid4)`),
  not UUIDv7. Sortable-ID invariant (AGENTS §6, data §3) unmet.
- **[liability]** Money: only `RefundRequest.amount: float` (`app/models/refunds.py:32`) —
  violates "integer minor units + ISO currency" (AGENTS I-16). No shared Money type.
- **[build]** No shared UUID/Money/tz-aware-datetime types; no request/actor/store/trace
  context object. (Trace-context envelope is co-owned with A02 — INTERFACE-REGISTRY.)

### API / contracts / errors / health
- **[facade]** Router registration: hand-wired in `app/main.py` (`api_v1.include_router(...)`
  ×24). A01 will publish a registry/convention so domains export a router + request
  registration without editing `main.py` ad hoc.
- **[reuse]** Contract pipeline: `scripts/export_openapi.py` → `openapi.json` →
  `frontend/orval.config.ts` (react-query, tags-split) → `frontend/src/api/generated/**`,
  via `frontend/src/api/mutator.ts`. Strong asset; becomes the `packages/contracts` spine.
- **[facade]** Errors: `app/core/error_handling.py` emits `{detail, request_id}` +
  `X-Request-Id` middleware. A richer `LLMErrorResponse{code,retryable,request_id}` exists
  in `app/schemas/errors.py` but is opt-in/doc-only. No runtime typed-error-code envelope
  (RISKS A01-R04). Target: the 15 normative codes (`03-ENGINEERING.md` §10).
- **[liability]** Health: `/health`, `/healthz`, `/readyz` all return `{ok:true}` with **no**
  dependency checks (`app/main.py:498-549`). Must implement the readiness dimensions in
  `05-OPERATIONS-AND-SECURITY.md` §11.1.

### Migrations / deps / tests
- **[reuse]** Alembic configured (`backend/alembic.ini`, `migrations/env.py` →
  `SQLModel.metadata`, `compare_type=True`), 34 revisions, single linear head
  **`a0b1c2d3e4f5`** (`add_store_profile`), startup auto-migrate via `init_db()`.
- **[reuse]** uv lockfile (`backend/uv.lock`), Python ≥3.12, fastapi 0.131, sqlalchemy
  2.0.46, sqlmodel 0.0.32, alembic 1.18.3, pydantic-settings 2.12, psycopg 3.3.2.
- **[liability]** Redis/RQ present (`redis`, `rq`) backing `app/services/queue.py` + rate
  limiting — v2 targets Postgres leased jobs (A02-owned migration; A09 compose cleanup).
- **[reuse]** ~90 pytest files incl. auth/identity/security tests (`backend/tests/`).
- **[reuse]** Secret store: `app/services/secret_store.py` (Fernet, handle-addressed).
  **[liability]** `Gateway.token` stored unencrypted (`app/models/gateways.py:25`).

## Current architecture

See `DIAGRAMS.md` (Current vs Target). Trust boundary today: browser → `customFetch`
(Bearer) → FastAPI `get_auth_context` → routers guarded by `deps.py`. No store-scope or
trace-context propagation exists yet.

## Dependencies

Consumes normative specs + A06 UI token/component contract (A01 owns identity/login/team
routes, so it is a route owner consuming A06 primitives) + A02 audit/trace sink (consumed
via an A01-owned no-op port until A02 ships). Exposes identity/request/actor/store/trace,
common types, typed errors, service-identity verification, channel-identity lookup, auth
dependency, health primitives, route-registration convention, and contract generation to
A02–A09. See `INTERFACES.md`.
