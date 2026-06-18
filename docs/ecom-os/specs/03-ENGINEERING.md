# 03 — Engineering

> **Status:** normative implementation practice  
> **Last reviewed:** 2026-06-18

This document defines how Ecom-OS is built. Product behavior belongs in the architecture
and specifications; these rules describe code boundaries, quality, testing, release
practice, and failure handling.

## 1. Engineering posture

Ecom-OS is an operational system. Correctness is not limited to returning HTTP 200. A
feature is incomplete until it has:

- durable state transitions;
- identity and store scoping;
- trace propagation;
- retry and concurrency semantics;
- user-visible failure behavior;
- migrations and rollback compatibility;
- tests at the risk boundary;
- documentation.

Prefer a small number of boring, explicit components over hidden framework magic.

## 2. Repository shape

The expected top-level structure is:

```text
/
├── AGENTS.md
├── README.md
├── compose.yaml
├── docs/
├── frontend/                  # Next.js + TypeScript
├── backend/
│   ├── app/
│   │   ├── api/               # authenticated transport only
│   │   ├── auth/              # users, roles, service identities
│   │   ├── domain/            # entities and pure domain rules
│   │   ├── events/            # inbox, outbox, projections
│   │   ├── jobs/              # leased Postgres jobs
│   │   ├── connectors/        # connector contracts + adapters
│   │   ├── actions/           # action ledger and executor
│   │   ├── traces/            # traces, spans, evidence, incidents
│   │   ├── hermes/            # bridge, capability probe, session mapping
│   │   ├── tools/             # versioned Ecom-OS tool catalog
│   │   ├── metrics/           # formulas, snapshots, freshness
│   │   ├── documents/         # vault metadata and search
│   │   └── extensions/        # Ecom-OS plugin host
│   ├── migrations/
│   └── tests/
├── hermes-integration/
│   ├── adapter/               # thin Hermes plugin package
│   ├── mcp/                   # remote MCP transport
│   ├── skills/                # Ecom-OS workflow skills
│   └── conformance/           # supported-Hermes test harness
├── extensions/                # built-in Ecom-OS extensions
├── scripts/                   # operator tooling; no app business logic
└── fixtures/                  # deterministic demo and test data
```

Core code never imports a user extension directly. Extensions register through the public
extension API.

## 3. Technology baseline

- Frontend: Next.js, React, TypeScript strict mode.
- Backend: Python 3.12+, FastAPI or an equivalent typed ASGI framework.
- Database: PostgreSQL 16+.
- Queue: Postgres-backed leased jobs in v1.
- Schema validation: Pydantic on the backend; generated TypeScript types for API/tool
  contracts.
- Database access: explicit transactions and migrations; ORM use is permitted only where
  generated SQL and locking semantics remain inspectable.
- Transport: HTTP/JSON, WebSocket/SSE, Hermes JSON-RPC, and MCP.
- IDs: UUIDv7 where available; opaque external IDs retained separately.
- Times: UTC in storage; IANA timezone at presentation and reporting boundaries.
- Money: integer minor units plus ISO currency. Never binary floating point.

Dependencies are pinned by lockfile. Production images are built from exact commits.

## 4. Boundary rules

### 4.1 Frontend

The frontend:

- renders state and collects intent;
- never decides whether a privileged action may execute;
- never holds Hermes, connector, database, or service credentials;
- never fabricates successful optimistic state for an external side effect before the
  backend has accepted an action;
- may optimistically update reversible local UI state, such as filters or draft text;
- always displays trace links and freshness where required by the spec.

### 4.2 API layer

API handlers:

- authenticate and parse;
- call application services;
- return typed errors;
- do not contain connector, policy, or database orchestration logic;
- attach user, instance, request, and trace context;
- do not expose stack traces or plaintext secrets.

### 4.3 Domain layer

Domain code:

- is transport-independent;
- expresses state transitions and invariants;
- avoids connector-specific payloads;
- uses explicit result types for expected failure;
- emits domain events rather than invoking external services inside transactions.

### 4.4 Connector adapters

Adapters:

- translate stable domain requests to provider calls;
- pin exact connected account and store;
- expose provider idempotency and reconciliation capabilities;
- normalize errors into typed categories;
- return provider request IDs and redacted diagnostics;
- never decide Ecom-OS autonomy policy;
- never write directly to unrelated domain tables.

### 4.5 Hermes integration

Hermes code in Ecom-OS:

- speaks documented protocols;
- sits behind `HermesBridge` and `HermesToolTransport` interfaces;
- never mutates Hermes SQLite or profile files during ordinary runtime;
- treats hook delivery as best-effort telemetry;
- records Hermes version and capability results;
- fails a dependent feature with an actionable code when the runtime contract is missing.

## 5. Contract-first development

The following contracts are versioned before implementation:

- Ecom-OS public HTTP API;
- Ecom-OS tool catalog and JSON schemas;
- action request and result envelope;
- trace event envelope;
- Hermes adapter telemetry envelope;
- connector interface;
- extension API;
- migration compatibility range.

Schemas generate test fixtures and client types. A breaking tool change creates a new tool
version or name; it does not silently alter meaning for existing skills or traces.

## 6. Trace context propagation

Every request, job, event, Hermes run, tool call, action, and connector attempt carries or
creates:

- `trace_id`;
- `span_id`;
- `parent_span_id` where known;
- `request_id` or `job_id`;
- `actor_type` and `actor_id`;
- `store_id` when applicable;
- `hermes_profile_id`, `hermes_session_id`, and `hermes_turn_id` when available.

Use W3C Trace Context on HTTP boundaries where possible. Persist domain trace records in
Postgres even when OpenTelemetry is also exported. A vendor observability backend is not
the product source of truth.

Logs are structured and include correlation IDs, but logs do not replace trace records.

## 7. Event and job semantics

### 7.1 Inbox processing

Inbound handlers perform only:

1. size and content-type limits;
2. source authentication/signature verification;
3. minimum envelope validation;
4. durable insert or duplicate recognition;
5. provider acknowledgement.

Full parsing and business processing happen asynchronously.

### 7.2 Job leases

A worker claims a job with a lease. The worker heartbeat extends the lease. If the process
dies, another worker may reclaim it after expiry. Handlers must therefore be idempotent.

Each job declares:

- type and schema version;
- deduplication key;
- concurrency key;
- attempt and maximum attempts;
- next run time;
- lease owner and expiry;
- trace ID;
- terminal error classification.

### 7.3 Ordering

Do not assume global event order. Serialize only where business state requires it, usually
by ticket, order, customer, or store. Compare provider occurrence timestamps and sequence
numbers where supplied. Store both `occurred_at` and `received_at`.

### 7.4 Outbox

Any state transition requiring external follow-up writes an outbox entry in the same
transaction. Outbox delivery is idempotent and trace-linked.

## 8. Action execution rules

An external write is never a bare connector call from a route, component, prompt, plugin,
or job. It is an action.

The action service must:

- normalize and freeze arguments;
- create the action before execution;
- calculate a stable action digest;
- resolve identity, grant, mode, policy, and approval;
- pin the target connection;
- record every attempt;
- use provider idempotency where available;
- distinguish retryable, permanent, rejected, and ambiguous failures;
- reconcile ambiguous outcomes;
- emit a final domain event;
- expose the trace URL in the tool response.

Unrestricted mode skips optional policy/approval gates only. No code path may skip action
creation, idempotency, store binding, or trace recording.

## 9. Concurrency and idempotency

Idempotency is enforced with database constraints, not only application-generated strings.

Examples:

- unique provider event ID per source and connection;
- unique external message ID per inbox;
- unique intent key per action scope;
- unique active reply action per ticket/message intent;
- unique provider idempotency key per action attempt;
- compare-and-set ticket ownership and state transitions.

Two workers handling the same ticket must not both send. Use row locks or advisory locks
around short critical sections. Never hold a database transaction open across a model or
network call.

## 10. Error model

Every expected error has:

- stable machine code;
- human-readable message;
- retry classification;
- trace ID;
- safe details;
- optional remediation.

Minimum categories:

- `validation_error`;
- `unauthenticated`;
- `forbidden`;
- `grant_disabled`;
- `approval_required`;
- `policy_rejected`;
- `resource_conflict`;
- `stale_state`;
- `connector_unavailable`;
- `rate_limited`;
- `outcome_unknown`;
- `hermes_unavailable`;
- `hermes_incompatible`;
- `dependency_unavailable`;
- `internal_error`.

The user interface matches the channel to the problem:

- field error for validation;
- inline action state for pending/failed actions;
- page banner for degraded dependencies;
- toast for transient local acknowledgement;
- incident banner for unresolved operational risk;
- route error boundary as the final UI floor.

“Never crash” is not an engineering claim. The requirement is: contain faults, preserve
accepted state, communicate clearly, and recover deterministically.

## 11. Hermes compatibility engineering

### 11.1 Pinning

Production declares:

- tested minimum and maximum Hermes versions;
- required adapter version;
- required protocol capabilities;
- optional capabilities with graceful degradation.

### 11.2 Startup probe

The probe records:

- Hermes version and profile;
- API and JSON-RPC health;
- `/v1/capabilities` result where available;
- adapter handshake and schema version;
- tool registration health;
- configured native channels and home channel;
- cron availability;
- session create/resume test;
- test Ecom-OS read-tool invocation;
- observer telemetry round trip.

Do not refuse to start all of Ecom-OS because one optional channel is absent. Disable or
degrade the dependent feature and surface health.

### 11.3 Conformance suite

The suite runs against every supported Hermes release and verifies the behaviors defined
in `ECOM-OS-RUNTIME-SPEC.md`. It is a release gate, not a manual checklist.

## 12. Testing strategy

Effort follows operational risk.

### 12.1 Required test layers

- **Pure unit tests:** formulas, state transitions, policy evaluation, redaction,
  identifiers, serializers.
- **Database tests:** constraints, locks, job leases, migrations, outbox, idempotency,
  action transitions.
- **Contract tests:** tool schemas, connector adapters, Hermes bridge, extension API.
- **Hermes conformance tests:** real supported Hermes process with adapter and fake Ecom
  server.
- **Connector sandbox tests:** provider test stores/accounts when available.
- **End-to-end tests:** browser + API + worker + Postgres + Hermes + fake or sandbox
  connectors.
- **Fault-injection tests:** timeouts, duplicated events, process death, reordered events,
  partial connector success, lost observer telemetry.
- **Security tests:** auth, role scope, channel identity, secret redaction, cross-store
  denial, untrusted content, plugin trust labels.
- **Restore tests:** automated backup, destructive change, restore, and consistency check.

### 12.2 Invariants tested first

Tests must prove:

- an Ecom-OS write cannot occur without an action row;
- an action is bound to one exact store and connection;
- duplicate delivery cannot duplicate the supported side effect;
- unrestricted mode does not invoke hidden business caps;
- restricted modes enforce their declared behavior;
- every Ecom-OS tool returns a trace reference;
- a Hermes session and Ecom-OS trace can be cross-located;
- sticky escalation follows configured rules;
- unknown connector outcomes are not blindly retried;
- no secret appears in logs, traces, API responses, or tool output;
- the main chat uses the real Hermes session system;
- daily brief numbers match the stored deterministic snapshot;
- direct/observed tools are never mislabeled as verified.

### 12.3 Test data

Fixtures use fictional customers, stores, addresses, and credentials. Production payloads
must never be copied into public test fixtures.

## 13. Database migrations

Migrations are:

- ordered and immutable after release;
- idempotent where operational tooling may re-run them;
- tested from every supported previous release;
- forward-compatible during rolling service restarts where possible;
- separated into expand, backfill, and contract phases for risky changes;
- instrumented with duration and row counts;
- blocked when required backups or compatibility checks fail.

Application code does not assume a destructive down migration is safe. Recovery normally
restores a snapshot or deploys forward-compatible code.

## 14. Security engineering

- Secrets live in runtime secret stores or appropriately scoped profile `.env` files.
- Secrets are redacted before logs, traces, exceptions, and model/tool output.
- Service credentials are least-privileged and independently rotatable.
- Browser-to-backend sessions use secure cookies, CSRF protection, and origin checks.
- Webhooks require verified signatures or mutually authenticated internal transport.
- The Ecom-OS-to-Hermes bridge remains on a private network/loopback boundary.
- Channel identities must map explicitly to Ecom-OS identities before privileged tools
  are available.
- File and attachment processing applies size, type, path, and decompression limits.
- HTML is sanitized; remote content remains untrusted.
- Trusted native extensions are visible in health and cannot masquerade as sandboxed.
- Dependency and image scanning run in CI; findings have ownership and severity policy.

Security controls should be explicit about what they protect. User autonomy is not an
excuse to blur credential or identity boundaries.

## 15. Observability

### 15.1 Product observability

The product includes:

- trace explorer;
- action ledger;
- event and job queues;
- connector health;
- Hermes health and compatibility;
- daily brief delivery status;
- incident records;
- data freshness and coverage.

### 15.2 Infrastructure observability

Export metrics for:

- request rate/error/latency;
- job age, attempts, leases, and dead letters;
- inbox/outbox backlog;
- action states and outcome-unknown age;
- connector latency/rate limits;
- Hermes run latency, errors, tokens, and adapter loss;
- database connections, locks, storage, and migration state;
- backup age and restore-test age.

Alerts route through the operator's configured mechanism, which may include Hermes native
channels, but critical infrastructure alerts must have a non-LLM delivery fallback.

## 16. Frontend and design system

The interface is calm, dense enough for operations, and trace-first.

### Required principles

- shadcn/ui or equivalent accessible primitives;
- one centralized token system;
- full keyboard navigation for core operations;
- readable tabular figures and money formatting;
- explicit loading, empty, stale, partial, error, and permission states;
- every mutable KPI shows freshness and source coverage;
- every action shows current state and trace link;
- motion supports orientation and feedback, not decoration;
- `prefers-reduced-motion` is honored;
- no animation requirement may delay operational correctness.

### Optimistic UI

Optimistic rendering is allowed only for reversible local or database-confirmed actions.
An external refund, message, cancellation, or discount is never shown as completed before
the action ledger records a confirmed or reconciled success.

## 17. Performance targets

Initial service-level objectives are design targets, not marketing guarantees:

- structured page API p95 under 500 ms for indexed local reads;
- chat first streamed event under 2 seconds excluding provider/model latency where
  Hermes supports it;
- accepted webhook persisted before provider timeout budget;
- new inbox event visible in queue within 10 seconds under normal load;
- trace search p95 under 1 second for a 90-day, single-brand dataset;
- daily brief delivered within 15 minutes of its scheduled window;
- no supported external action duplicated under retry tests.

Measure before introducing caches or a separate queue broker.

## 18. Pull requests and change discipline

- One coherent vertical slice per pull request.
- Security- and money-relevant changes are tests-first.
- Every schema/tool/API change includes generated contracts and migration notes.
- Every user-visible behavior includes empty, error, permission, stale, and trace states.
- Every Hermes integration change runs the conformance suite.
- Every connector write change runs duplicate, timeout, and reconciliation tests.
- A short `docs/changes/` note records behavior and operator impact.
- Code and normative documents are updated together.

### Definition of done

A slice is done only when:

- lint, type checks, unit, integration, and required E2E tests pass;
- migrations pass supported upgrade tests;
- endpoints and sockets are authenticated;
- trace linkage is present;
- no secret is emitted;
- accessibility checks pass for the surface;
- health/degradation behavior is implemented;
- operator documentation is updated;
- acceptance criteria in the build spec are met.

## 19. Dependency and framework policy

Do not build core guarantees on an undocumented convenience API. For Hermes, connectors,
and frontend frameworks:

- wrap dependencies behind owned interfaces;
- pin versions;
- record required capabilities;
- test real integrations;
- keep a graceful fallback where practical;
- remove dead compatibility code deliberately.

Framework popularity is not an architectural rationale. A decision must be grounded in a
required capability, operational cost, and replacement path.
