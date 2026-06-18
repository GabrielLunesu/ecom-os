# A01 — Platform Foundation and Identity — Diagrams

## Current (audited at 3909904)

```mermaid
flowchart LR
  Browser["Next.js (frontend/src/api/mutator.ts)"] -- "Bearer (Clerk JWT or local static token)" --> API
  subgraph API["FastAPI — Mission Control API (app/main.py)"]
    AC["get_auth_context / AuthContext (core/auth.py)"]
    DEPS["deps.py: require_user_auth / require_org_member / require_org_admin"]
    R["24 hand-wired routers (api_v1.include_router)"]
    ERR["error_handling.py: {detail, request_id}"]
    H["/health /healthz /readyz -> {ok:true} (no checks)"]
  end
  AC --> DEPS --> R
  R --> DB[("Postgres 16 (SQLModel, uuid4 ids, naive UTC, float money)")]
  R -. "agents" .-> AGENTAUTH["agent_auth.py (X-Agent-Token, PBKDF2)"]
  API -. "Redis/RQ queue + rate limit" .-> REDIS[("Redis (to be replaced by PG jobs)")]
  API -- "scripts/export_openapi.py" --> OAPI["openapi.json"]
  OAPI -- "orval" --> GEN["frontend/src/api/generated"]
```

Gaps vs v2: no owner-bootstrap close, no Role/Permission/channel-identity tables, no
UUIDv7/Money/tz-aware types, no request/actor/store/trace context, no typed error codes at
runtime, health checks are stubs.

## Target

```mermaid
flowchart TB
  subgraph Edge["Trust boundary: untrusted client"]
    Browser["Next.js routes (A06 primitives)"]
  end
  Browser -- "session cookie / Bearer; CSRF + origin checks" --> APIGW

  subgraph APIGW["backend/app/api (transport + auth only)"]
    MW["RequestContext middleware: request_id, W3C traceparent -> trace_id/span_id, actor, store_scope"]
    DEP["Depends(authn) -> ActorContext (human|service|channel)"]
    REG["router registry: domains export router; A01 convention registers"]
    ERRV["typed Error envelope {code,message,retryable,trace_id,details?,remediation?}"]
  end

  subgraph Foundation["backend/app/auth + app/core (A01-owned)"]
    BOOT["owner bootstrap (closes after first owner)"]
    IDENT["users / roles / role_permissions / service_identities / channel_identities"]
    TYPES["common types: Uuid7, Money(minor+ISO), utc datetime, typed errors"]
    HEALTH["/health: liveness, readiness(read/run/write), connectors, queue, traces, backup, compat"]
    PORT["AuditTraceSink port (no-op fake until A02)"]
  end

  DEP --> IDENT
  MW --> ERRV
  REG --> ERRV
  BOOT --> IDENT
  DEP -- "ActorContext + StoreScope" --> Domains["A02-A09 domain routers"]
  Foundation --> DB[("Postgres: UUIDv7, integer minor-unit money, UTC, encrypted secrets")]
  PORT -. "consumed when available" .-> A02[("A02 trace/action/audit core")]
  Foundation -- "Pydantic schemas -> OpenAPI -> packages/contracts (TS client)" --> Browser
```

Trust boundaries: the browser is never an authorization boundary (AGENTS §7); effective
identity/scope is re-resolved server-side at request and tool-invocation time (Runtime
§6.2). Secrets stay handles/ciphertext (AGENTS I-15). Every request carries or creates a
trace context (`03-ENGINEERING.md` §6); coverage labels are `verified|observed|imported|unknown`.
