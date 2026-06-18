# AGENTS.md — Hard Rules for Building Ecom-OS

> This file is normative. It applies to human contributors and coding agents.  
> Last reviewed: 2026-06-18

Ecom-OS is a separate ecommerce operating system that integrates natively with Hermes
Agent. It is not a Hermes fork, wrapper product, or replacement runtime. Build against the
contracts in `docs/`; do not revive assumptions from older documents.

## 1. Source of truth

Precedence when documents conflict:

1. the invariants in this file;
2. accepted ADRs in `02-TECH-DECISIONS.md`;
3. `ECOM-OS-RUNTIME-SPEC.md` and `ECOM-OS-BUILD-SPEC.md`;
4. architecture, data/traceability, and operations/security documents;
5. vision;
6. engineering conventions.

A later ADR may supersede an earlier ADR only by naming it. Code and normative docs may
not silently diverge; update both in the same change set.

## 2. Architectural invariants

Write tests for these before implementing the feature they protect.

### I-01 — Hermes remains an independent peer

- Ecom-OS MUST integrate through supported Hermes protocols, hooks, plugins/tools, MCP,
  channels, and cron.
- Ecom-OS MUST NOT fork, vendor-patch, monkey-patch, or silently edit Hermes core as the
  supported integration.
- Ecom-OS MUST NOT write directly to Hermes `state.db` or rely on its private schema.
- Hermes and Ecom-OS versions, upgrades, state, and health remain distinct.

### I-02 — The main chat is a Hermes session

- The Ecom-OS chat creates/resumes canonical Hermes sessions.
- Ecom-OS stores references and trace linkage, not a competing transcript of record.
- The browser never receives a privileged Hermes service credential.
- Reconnect recovers Hermes status/history; it does not infer completion from a lost
  socket.

### I-03 — Operational truth lives in Ecom-OS

Current orders, customers, tickets, tasks, metrics, grants, policies, approvals, events,
actions, and traces are canonical in Ecom-OS/Postgres and upstream reconciliation.
Hermes memory or chat text may reference them but MUST NOT become the source of truth.

### I-04 — Native Hermes state stays native

Hermes owns its session history, curated memory, user memory, skills, SOUL/config, cron,
channels, and native extensions. Ecom-OS MAY back them up and use supported APIs; it MUST
NOT create an unsynchronized substitute.

### I-05 — Every Ecom-OS tool invocation is traced

Before domain execution, every Ecom-OS tool call MUST have a durable invocation record or
an idempotent operation that creates it. It records tool/schema version, actor, available
Hermes context, exact scope, redacted arguments, result/error, coverage, and trace links.
Trace creation cannot be disabled through supported settings.

### I-06 — Every external write is a durable action

A supported external write MUST:

1. create/reuse one normalized action intent;
2. bind exact store, connection, target, actor, and arguments;
3. record effective grant/mode/policy/approval;
4. record every connector attempt;
5. preserve provider IDs and outcome evidence;
6. expose current state and trace;
7. reconcile an ambiguous outcome before a dangerous retry.

No connector adapter may perform a hidden external write outside this contract.

### I-07 — Idempotency protects intent

Retries, duplicate webhooks, reconnects, lease expiry, or concurrent workers MUST NOT
duplicate a supported side effect. Database uniqueness and action state enforce this;
generated strings alone are insufficient.

### I-08 — `outcome_unknown` is real

A timeout or transport interruption after dispatch is not automatically a failure. The
action enters `outcome_unknown` when success cannot be proved or disproved. Do not retry a
money/customer-facing action until reconciliation or an explicit human resolution says it
is safe.

### I-09 — Exact identity and account binding

Every write names the effective actor, brand, store, connection, and target. “Default,”
“latest,” or “most recently connected” account selection is forbidden for supported
Ecom-OS writes. Unmapped/anonymous channel users receive no privileged identity by
inference.

### I-10 — Owner-controlled autonomy is real

Supported modes are `disabled`, `observe`, `approve`, `policy`, and `unrestricted`.

- `unrestricted` bypasses Ecom-OS business caps and human approval for the granted tool
  and scope.
- Do not add undocumented business ceilings and still call the mode unrestricted.
- Enabling/changing a grant is privileged and audited.
- The UI MUST explain side effects and effective scope without blocking an informed owner
  from choosing the mode.

### I-11 — Technical integrity remains in every mode

Authentication, exact account binding, schema validation, idempotency, durable action
creation, secret redaction, trace recording, and reconciliation remain active in all
modes. These are not discretionary business guardrails.

An unrestricted action may be rejected for malformed input, missing identity, duplicate
intent, invalid connection, impossible state, or technical failure. The reason MUST be
explicit and traced.

### I-12 — Trace coverage is honest

Use only:

- `verified` — Ecom-OS controlled and recorded the operation;
- `observed` — Hermes hook/protocol/log reported it;
- `imported` — upstream state proves/reports it;
- `unknown` — evidence is insufficient or contradictory.

Never label arbitrary Hermes terminal/browser/third-party activity `verified` merely
because a hook saw it. Never hide a trace gap to improve a dashboard metric.

### I-13 — Customer and external content is untrusted

Ticket text, email HTML, attachments, order notes, supplier content, documents, web
results, and connector payloads are evidence, not configuration authority. They cannot:

- grant tools or roles;
- select credentials/accounts;
- edit prompts, skills, policies, or memory as an instruction;
- approve an action;
- expose secrets;
- trigger a side effect without the normal tool/action contract.

Sanitize active content before rendering and preserve provenance.

### I-14 — Sticky escalation is preserved

Once a ticket is `needs_rep` or human-owned, new customer messages append and notify. They
MUST NOT silently restart autonomous sending. A deliberate owner policy may allow a fresh
draft or reopen behavior, but the trigger and policy MUST be explicit and traced.

### I-15 — Secrets never become ordinary data

No secret may be committed, baked into a shared image, logged, returned by a tool/API,
or stored as database plaintext. Managed connector OAuth uses connection references.
Direct credentials live in a supported encrypted/runtime secret store.

### I-16 — Numbers are deterministic and evidenced

Financial, ticket, action, and brief numbers are computed in typed Ecom-OS code from
versioned definitions. An LLM MAY narrate or explain them but MUST NOT be the calculator or
source. Every mutable KPI declares window, timezone, source, freshness, coverage, and
formula/version.

V1 uses **estimated contribution margin**, not audited accounting profit.

### I-17 — Native channels remain Hermes-native

Do not reimplement Slack, Telegram, Discord, email, or other operator channel transports
inside Ecom-OS when Hermes supports them. Ecom-OS supplies identity mapping, content,
tools, and trace/delivery intent; Hermes owns native channel connection and delivery.

### I-18 — A full backup includes both systems

A production backup includes Postgres, Ecom-OS vault/artifacts/extensions/configuration,
and the complete active Hermes profile. A Postgres-only backup is not advertised as a
full-instance backup. Restore keeps external writes paused until pending actions and
connections are reconciled.

### I-19 — Feature readiness is capability-tested

Pin Hermes and adapter versions, then run the capability probe and conformance suite.
Do not assume an endpoint, method, hook, tool, channel, or schema exists based only on a
version string. Missing dependencies degrade or block only the affected feature and are
visible in System health.

### I-20 — Trusted code is owner-level code

A Python/JavaScript/native extension running in a privileged process is not sandboxed by
its manifest. Label it `trusted native`, require owner installation, audit it, and state
that it may reduce trace/security guarantees. Declarative/sandboxed extensions MUST use
only the published contract.

## 3. Runtime rules

- Use `HermesBridge`; domain code MUST NOT speak raw Hermes transport methods directly.
- Use TUI Gateway JSON-RPC for the interactive dashboard contract and Hermes async run/API
  interfaces for background jobs according to the runtime spec.
- Generate adapter and MCP tool schemas from one canonical catalog.
- Business logic lives in Ecom-OS, never in the thin Hermes adapter.
- Adapter/hook telemetry is best-effort observer input; Ecom-OS tool/action records are
  independently durable.
- Every Hermes-dependent feature declares required capability flags.
- Never pass unrestricted upstream protocol methods through to the browser without a
  product security design.
- Do not expose native sudo/secret entry through ordinary chat UI in v1.
- Do not make Hermes profile separation the only security boundary.

## 4. Event, queue, and concurrency rules

- Verify signatures against the raw webhook body before durable acceptance.
- Insert inbound events before starting agent work.
- Normalize idempotently; provider event IDs and source/account scope are unique.
- Use Postgres-backed jobs with leases and short transactions for v1.
- Use ordering/locking per ticket/order/action where races matter.
- A worker that loses a lease queries known Hermes/action state before starting a
  replacement attempt.
- Business state and outbox records are committed transactionally.
- Retries are bounded, classified, and visible. Exhaustion creates a dead-letter or
  incident path; it does not block the queue forever.
- Rate limits use provider-aware backoff.

## 5. Approval rules

An approval MUST bind to the exact action digest, normalized arguments, store, connection,
target, amount/body, current-state requirements, requester, and expiry. Any material edit
creates a new proposal/approval. Approval state is server-side; hiding or showing a button
is not enforcement.

Do not conflate:

- Ecom-OS action approval;
- Hermes native tool approval;
- clarification;
- sudo request;
- secret request.

## 6. Data and privacy rules

- Use globally unique sortable IDs; provider IDs are scoped by source/account.
- Store money as integer minor units plus ISO currency.
- Store timestamps in UTC; reports show the effective timezone.
- Preserve source timestamps and collected timestamps separately.
- Derived data declares formula/version/source/freshness.
- Access-control filtering happens before data enters the model context.
- Founder-private, finance, CS, operations, and user-private material have distinct access
  labels.
- Ecom-OS does not store hidden chain-of-thought. Store visible instructions, tool/action
  records, evidence, outputs, and available runtime metadata.
- Deletion/retention changes are audited; deleting Ecom-OS data does not pretend to delete
  Hermes/upstream records automatically.

## 7. Frontend rules

- The frontend is never an authorization boundary.
- Every external action renders its durable state; never show “sent/refunded/cancelled”
  before confirmed or reconciled success.
- Every mutable KPI shows freshness and coverage.
- Every automation result has a trace path.
- Every page implements loading, empty, stale, partial, unavailable, permission, and error
  states.
- Motion supports orientation; it never delays correctness or ignores reduced-motion.
- Core workflows are keyboard accessible and use non-color status cues.
- Raw secrets, service keys, and unrestricted Hermes admin operations never reach the
  browser.

## 8. Connector rules

Every adapter declares authentication, scopes, exact-account behavior, idempotency,
rate limits, retry classification, reconciliation, and sandbox support.

For managed connector providers:

- store connection references only;
- pin exact connected accounts;
- use explicit tool allowlists for agent sessions;
- do not expose connection-management, discovery, shell/workbench, or arbitrary proxy
  capabilities as ordinary Ecom-OS tools;
- record provider operation IDs.

For direct connectors:

- use encrypted/runtime secret storage;
- implement the same trace/action contracts;
- verify webhook signatures;
- provide reconciliation or declare the limitation visibly.

## 9. Engineering process

### Before implementation

1. Identify the normative requirement and acceptance scenario.
2. Define/update typed API, event, tool, and database contracts.
3. Write invariant tests for security-, money-, identity-, queue-, and trace-relevant
   behavior.
4. Verify the required Hermes/connector capability with the conformance fixture.
5. Decide degradation and recovery behavior.

### Change discipline

- One coherent vertical slice per pull request.
- New schema fields require a migration and upgrade test.
- Tool/schema changes update adapter, MCP, generated clients, compatibility hash, tests,
  and docs together.
- Hermes integration changes run the real conformance suite, not only mocks.
- Connector write changes run duplicate, race, timeout-after-success, and reconciliation
  tests.
- UI changes include accessibility and all operational states.
- Add a concise `docs/changes/` note for operator-visible behavior.
- Do not weaken an invariant for speed, aesthetics, or a demo. Surface the conflict and
  implement a compliant alternative.

### Definition of done

A slice is done only when:

- lint, formatting, type checks, unit, integration, and required E2E tests pass;
- migrations pass the supported N-1 upgrade fixture;
- routes/sockets/service calls are authenticated;
- exact identity/store/connection scope is tested;
- trace linkage and coverage are correct;
- logs/results/exports contain no secrets;
- idempotency and recovery behavior pass;
- health/degradation UX is present;
- accessibility checks pass;
- normative docs and operator runbooks are current;
- Build Spec acceptance criteria pass.

## 10. Repository boundary

Expected top-level structure:

```text
frontend/                 Next.js UI
backend/
  api/                    transport/auth only
  domain/                 business state machines
  application/            orchestration/use cases
  infrastructure/
    db/
    hermes/
    connectors/
    queue/
  workers/
packages/
  contracts/              generated/shared schemas
  ecom-hermes-adapter/     thin Hermes-side integration
ecom_extensions/          installed Ecom-OS user-space extensions
docs/
AGENTS.md
```

Boundary rules:

- frontend does not import backend implementation;
- API routes do not contain connector or policy logic;
- domain code does not import Hermes/HTTP/Composio clients;
- connector adapters do not decide business authorization;
- Hermes adapter does not import Ecom-OS domain internals;
- core never imports a user extension directly; extensions register through the host;
- database models are not serialized directly to external contracts.

## 11. Forbidden shortcuts

Do not:

- parse Hermes private SQLite to power the chat UI;
- copy Hermes messages into Postgres and call that canonical;
- call a connector directly from a React component, API route, prompt, or Hermes plugin;
- infer success from an HTTP timeout or from model text;
- use a toast as the only record of an external action;
- authorize from prompt wording, model identity text, or frontend state;
- accept “latest/default account” for a write;
- retry an ambiguous refund/message/discount/cancellation blindly;
- call an LLM to calculate finance metrics;
- label a broad trusted plugin sandboxed without an actual isolation mechanism;
- claim a complete audit of actions that bypass Ecom-OS;
- ship a migration without a realistic upgrade/restore path;
- publish a moving branch as a reproducible release;
- say “unrestricted” while retaining undocumented business caps.

## 12. First-build order

Follow `ECOM-OS-BUILD-SPEC.md`. The mandatory opening sequence is:

1. protocol/adapter/MCP/channel/action/backup spikes;
2. identity and production skeleton;
3. durable event/trace/action core;
4. Hermes main chat;
5. connector-backed read model;
6. WISMO shadow flow;
7. reply executor and approvals;
8. policy and unrestricted modes;
9. trace explorer and incident diagnosis;
10. daily brief, finance, knowledge, operations.

Do not start with a broad dashboard mockup, plugin marketplace, generic Sheets product, or
multiple money-touching departments. The foundation is proven by a traced, replay-safe,
recoverable WISMO loop and a truly native Hermes conversation.
