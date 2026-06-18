# 04 — Data and Traceability

> **Status:** normative data contract  
> **Last reviewed:** 2026-06-18

Traceability is a primary product feature. This document defines how Ecom-OS represents
business state, agent work, external actions, evidence, and administrative changes so a
human or Hermes can reconstruct what happened later.

## 1. Design goals

The data model must support:

- thousands of tickets and many more messages/tool calls per month;
- search by business entity, person, agent, date, tool, outcome, or error;
- exact linkage between Hermes sessions and Ecom-OS work;
- deterministic reconstruction of supported external actions;
- honest representation of partial visibility;
- replay of durable events without repeating side effects;
- retention and privacy controls;
- incident review and agent-assisted diagnosis;
- migration without invalidating historical traces.

The model is **not** a pure event-sourced system. Current operational state lives in
normalized tables. Immutable events and trace records explain how that state changed.

## 2. Terminology

- **Domain entity:** order, ticket, message, customer, task, document, store, connection,
  policy, or another business object.
- **Event:** an immutable fact accepted by Ecom-OS.
- **Trace:** a causal or correlated unit of work.
- **Run:** one Hermes turn/background execution or one deterministic workflow execution.
- **Span:** a timed operation inside a trace.
- **Tool invocation:** a model- or human-requested call to a versioned Ecom-OS or observed
  Hermes tool.
- **Action:** an intended external side effect under Ecom-OS control.
- **Attempt:** one request to a connector/provider while completing an action.
- **Evidence:** a source record, document excerpt, metric input, or observation used by a
  run or decision.
- **Approval:** a decision by an authorized person about an exact action digest.
- **Audit record:** an administrative/configuration change.
- **Incident:** an operational problem requiring investigation or remediation.

## 3. Identifier rules

Ecom-OS generates UUIDv7 identifiers for new internal records where supported. IDs are
opaque to clients.

Required correlation identifiers include:

| Identifier | Purpose |
|---|---|
| `event_id` | One accepted immutable event. |
| `trace_id` | Top-level correlated activity. |
| `span_id` | One operation inside a trace. |
| `run_id` | One Hermes or deterministic execution. |
| `tool_invocation_id` | One tool request/result pair. |
| `action_id` | One intended external side effect. |
| `attempt_id` | One connector request. |
| `approval_id` | One approval decision. |
| `incident_id` | One investigation/remediation record. |
| `request_id` | One inbound API request. |
| `job_id` | One durable background job. |

External provider IDs are stored in separate fields with provider and connection scope.
Never use an external ID alone as a global identifier.

## 4. Common event envelope

Every accepted event uses a versioned envelope. Provider payloads may be nested under
`data`, but the envelope remains stable.

```json
{
  "event_id": "019...",
  "event_type": "ticket.message.received",
  "schema_version": 1,
  "source": "gmail",
  "source_event_id": "provider-id",
  "brand_id": "019...",
  "store_id": "019...",
  "connection_id": "019...",
  "trace_id": "019...",
  "causation_event_id": null,
  "correlation_key": "ticket:019...",
  "occurred_at": "2026-06-18T08:41:00Z",
  "received_at": "2026-06-18T08:41:03Z",
  "actor": {
    "type": "external_customer",
    "id": "customer:019..."
  },
  "coverage": "imported",
  "data": {},
  "metadata": {
    "payload_hash": "sha256:...",
    "verification": "valid"
  }
}
```

Required characteristics:

- immutable after acceptance except processing metadata stored separately;
- schema versioned;
- source and exact connection identified;
- occurrence and receipt time separated;
- payload hash retained;
- PII classification attached by processing;
- duplicate recognition based on source identity and payload semantics.

## 5. Core relational model

The exact migrations may evolve, but the conceptual tables and relationships are
normative.

### 5.1 Instance and identity

#### `brands`

- `id`
- `name`
- `default_timezone`
- `default_currency`
- `created_at`, `updated_at`

Exactly one active brand exists per instance.

#### `stores`

- `id`, `brand_id`
- `name`, `platform`, `external_store_id`
- `timezone`, `currency`
- `status`
- `created_at`, `updated_at`

#### `users`

- `id`
- `email`, `display_name`
- `status`
- authentication metadata reference
- `created_at`, `last_seen_at`

#### `roles`, `user_roles`, `role_permissions`

Human authorization is explicit and auditable.

#### `service_identities`

- Ecom workers;
- Hermes integration adapter;
- connector callbacks;
- extension services.

Each identity has narrow scopes and rotatable credentials.

#### `channel_identities`

- `user_id`
- `hermes_profile_id`
- `platform`
- `platform_user_id`
- optional `chat_id` or `channel_id`
- effective role/scope override
- verification state

### 5.2 Hermes references

#### `hermes_profiles`

- `id`
- stable Ecom-OS alias
- Hermes profile name/home reference
- role: `primary`, `founder`, `finance`, `worker`, etc.
- adapter version
- last reported Hermes version
- compatibility state
- health/freshness timestamps

#### `hermes_sessions`

This is a reference index, not a transcript copy.

- `id`
- `hermes_profile_id`
- `hermes_session_id`
- optional `session_key`
- source platform
- mapped Ecom user/channel identity
- title and timestamps as derived metadata
- last observed model
- canonical Hermes link/locator
- last synchronized at

Uniqueness: `(hermes_profile_id, hermes_session_id)`.

#### `session_entity_links`

Links a Hermes session to tickets, orders, customers, incidents, tasks, or documents.
Links carry creator, reason, confidence, and timestamps.

### 5.3 Connections

#### `connections`

- `id`, `store_id`
- `provider` (`composio`, `direct_shopify`, etc.)
- `capability` (`store`, `inbox`, `ads`, `payments`, `supplier`)
- external connected-account reference
- secret reference where direct adapter requires it
- health state and last check
- metadata without plaintext secrets

Every connector request references one connection row.

### 5.4 Customer-service domain

#### `tickets`

- `id`, `store_id`, `inbox_connection_id`
- provider thread/conversation ID
- subject, normalized status, priority
- `owner_type`, `owner_id`
- autonomy state and sticky-escalation state
- customer ID
- first/last message timestamps
- current Hermes ticket session reference
- current trace/last run reference
- version for optimistic concurrency

#### `messages`

- `id`, `ticket_id`
- external message ID
- direction and sender type
- raw body reference and sanitized body
- untrusted flag
- received/sent timestamps
- attachment metadata
- linked send action for outbound messages
- payload/source evidence reference

#### `ticket_state_history`

Append-only record of ticket state, ownership, escalation, reopen, and automation changes.

### 5.5 Commerce and finance domain

Minimum normalized records:

- `customers`
- `orders`
- `order_lines`
- `fulfillments`
- `refunds`
- `transactions`
- `products`
- `variants`
- `suppliers`
- `cost_records` with effective dates
- `ad_spend_records`
- `fees`
- `shipping_costs`
- `fx_rates`
- `metric_snapshots`
- `metric_components`

Raw upstream payloads may be retained separately for reconciliation. Normalized rows store
source, connection, external version/update time, and last synchronized time.

### 5.6 Tasks and approvals

#### `tasks`

- title, description, status, priority;
- assignee user/profile;
- source trace/entity;
- due date;
- completion evidence.

#### `approvals`

- `id`, `action_id`
- exact `action_digest`
- requested by actor/run
- required permission/role
- status
- approver and decision time
- expiry
- comment
- optional conditions

An approval cannot authorize modified action arguments. Changing the action creates a new
digest and approval request.

### 5.7 Documents

#### `documents`

- stable ID and logical path;
- title, type, access label;
- current version;
- source and owner;
- checksum;
- effective and expiry dates;
- ingestion/search status.

#### `document_versions`

- immutable content reference;
- checksum;
- created by and source trace;
- supersedes relationship;
- extracted metadata.

#### `document_chunks` (optional in v1)

Used for full-text or semantic indexing. Every chunk references a document version and
must never outlive its provenance.

## 6. Trace model

### 6.1 `traces`

Required fields:

- `id`
- `trace_type` (`chat_turn`, `ticket_run`, `daily_brief`, `sync`, `action`, `incident`,
  `manual_operation`, etc.)
- title/summary
- brand/store scope
- root actor
- root event/request/job
- status
- coverage summary
- started/ended timestamps
- primary entity links
- parent trace when nested
- retention class

Trace status is derived from child records but materialized for fast queries.

### 6.2 `runs`

- `id`, `trace_id`
- runtime (`hermes`, `deterministic`, `human`)
- Hermes profile/session/turn/run references
- source platform
- model/provider when available
- prompt/skill/config versions or hashes when available
- status and end reason
- token/cost/latency metadata
- started/ended timestamps
- coverage

Ecom-OS does not store hidden chain-of-thought. It stores visible instructions, tool
interactions, output, decisions, and available runtime metadata.

### 6.3 `spans`

- `id`, `trace_id`, optional `run_id`
- parent span
- type (`trigger`, `retrieval`, `llm`, `tool`, `policy`, `approval`, `connector`,
  `calculation`, `delivery`, `reconciliation`, `human_change`)
- name
- status
- coverage
- actor and entity links
- timestamps and duration
- safe structured attributes
- error code/reference

Spans may be streamed into the UI while open. Completed records are immutable except for
late reconciliation metadata recorded as a new span/event.

### 6.4 `tool_invocations`

- tool name and version;
- transport (`hermes_adapter`, `mcp`, `dashboard`, `api`, `extension`);
- Hermes correlation fields;
- actor and effective identity;
- store and connection scope;
- redacted arguments plus encrypted/raw restricted reference if necessary;
- normalized result summary;
- start/end/status;
- coverage;
- linked action IDs;
- schema hash;
- error code;
- parent span/run/trace.

A write-capable Ecom-OS tool must create its invocation record before executing domain
logic.

## 7. Trace coverage

`coverage` is mandatory on runs, spans, tool invocations, and imported outcomes.

### `verified`

Ecom-OS executed the operation through a supported contract and durably recorded input,
state transition, and result.

### `observed`

A Hermes protocol event, plugin hook, gateway hook, or log adapter reported the operation,
but Ecom-OS did not control or independently verify the side effect.

### `imported`

An upstream webhook or synchronization proves or reports a business state change without
a corresponding verified Ecom-OS execution.

### `unknown`

The available facts do not identify a reliable execution path or outcome.

Coverage does not imply that the agent's judgment was correct. It describes evidence
quality and control of the execution path.

## 8. Action ledger

### 8.1 `actions`

Required fields:

- `id`, `trace_id`, `tool_invocation_id`;
- action type and schema version;
- exact store and connection;
- target entity/customer/order/ticket;
- normalized arguments;
- currency/minor units where relevant;
- action digest;
- requested actor/run/session;
- effective grant and autonomy mode;
- policy version and result;
- approval requirement and linked approval;
- idempotency intent key;
- state;
- timestamps;
- final outcome summary;
- reversibility/compensation metadata.

### 8.2 Action states

```text
proposed
  ├── simulated
  ├── rejected
  ├── awaiting_approval
  │      ├── rejected
  │      ├── expired
  │      └── authorized
  └── authorized
          └── executing
                 ├── succeeded
                 ├── failed_permanent
                 ├── failed_retryable
                 ├── outcome_unknown
                 │      ├── reconciled_succeeded
                 │      ├── reconciled_failed
                 │      └── manual_resolution
                 └── cancelled
```

State transitions are append-recorded in `action_state_history`. The current state is
materialized on `actions`.

### 8.3 `action_attempts`

- `id`, `action_id`, attempt number;
- connector and exact account;
- provider idempotency key;
- request fingerprint and safe request summary;
- provider request/operation IDs;
- started/ended timestamps;
- HTTP/provider status category;
- safe response summary;
- retry classification;
- outcome confidence;
- error reference;
- reconciliation due time.

A provider timeout does not erase the attempt. It creates an ambiguous record that can be
reconciled.

### 8.4 Intent idempotency

The idempotency key represents the operator/agent intent, not merely a network request.
Examples:

- reply once to a specific inbound message with a specific final body hash;
- refund a specific order amount for a specific reason/version;
- create one discount for a specific campaign/customer/period;
- cancel one order from one triggering decision.

Provider retry keys derive from `action_id` and attempt semantics. Database uniqueness
protects supported actions even when providers lack idempotency support.

## 9. Evidence and provenance

### 9.1 `evidence`

Evidence may point to:

- a ticket message;
- an order or line item version;
- a provider payload;
- a document version/chunk;
- a metric component;
- a policy version;
- a web research artifact;
- a human note;
- a Hermes session message reference;
- a connector response.

Fields include source, source timestamp, collected timestamp, trust label, access label,
content hash, excerpt/reference, and supersession state.

### 9.2 Evidence links

`evidence_links` connect evidence to runs, spans, tool invocations, actions, metric
snapshots, and incidents with a purpose:

- `input`;
- `support`;
- `contradiction`;
- `policy_basis`;
- `calculation_component`;
- `outcome_confirmation`;
- `human_review`.

A generated explanation is not evidence for itself.

## 10. Administrative audit

`audit_records` capture privileged changes such as:

- user/role changes;
- channel identity mapping;
- connector creation/removal;
- tool grant/autonomy changes;
- policy and prompt/skill configuration changes;
- approval decisions;
- extension installation;
- Ecom-OS or Hermes update operations;
- backup/restore operations;
- retention deletion/export;
- incident closure.

Each record includes before/after safe diffs, actor identity, source, trace, request,
reason/comment, and timestamp.

Audit and trace are related but distinct:

- trace explains operational work;
- audit explains control-plane changes.

A configuration change may appear in both when it directly causes a run.

## 11. Incident model

### `incidents`

- title and severity;
- detection source;
- affected stores/entities/time window;
- owner/status;
- root trace(s);
- suspected cause category;
- financial/customer impact estimate;
- containment and remediation tasks;
- timeline;
- resolution and lessons;
- linked policy/skill/config changes.

Cause categories should distinguish at least:

- agent judgment;
- prompt/skill configuration;
- owner policy/autonomy choice;
- stale or incorrect source data;
- connector/provider behavior;
- Ecom-OS defect;
- Hermes/runtime defect;
- human action;
- external fraud/customer behavior;
- unknown.

The system must not automatically blame the model when evidence is insufficient.

## 12. Agent-accessible trace tools

Hermes receives read tools designed for diagnosis:

- `ecom_trace_get(trace_id)` — complete structured trace summary.
- `ecom_trace_search(filters, query)` — search traces and actions.
- `ecom_trace_timeline(trace_id)` — ordered spans/events with coverage.
- `ecom_action_get(action_id)` — frozen intent, policy, attempts, outcome.
- `ecom_action_explain(action_id)` — facts and configuration that governed execution.
- `ecom_trace_compare(trace_ids)` — aligned differences across runs.
- `ecom_incident_create(...)` — open an incident with linked evidence.
- `ecom_incident_add_finding(...)` — append a finding or hypothesis.
- `ecom_metric_explain(snapshot_id)` — formula and source components.

Tool output is structured, paginated, access-controlled, and includes UI links. Large raw
payloads require explicit elevated access and are not injected by default.

## 13. Trace explorer requirements

The UI must support:

- full-text search over safe summaries;
- filters for date, store, ticket, order, customer, Hermes profile/session, user, model,
  tool, action type, autonomy mode, policy, status, error, and coverage;
- grouping by trace, ticket, customer, action, or incident;
- a chronological timeline;
- request/result and before/after safe diffs;
- evidence panel;
- action-attempt and reconciliation panel;
- related traces and causal links;
- “inspect in chat” action that opens/resumes Hermes with the trace selected;
- exports with redaction and access checks;
- saved searches for recurring investigations.

For a large month, the default view summarizes runs. Users opt into span-level detail.

## 14. Daily brief data model

### `daily_briefs`

- reporting date and timezone;
- window start/end;
- status;
- metric snapshot IDs;
- ticket/activity/action aggregates;
- unusual-event query and results;
- tasks due;
- health warnings;
- deterministic fallback text;
- Hermes run/session/cron references;
- generated final text;
- delivery targets and results;
- trace ID;
- created/finalized/delivered timestamps.

The input snapshot is immutable after finalization. A correction creates a new revision and
states what changed.

## 15. Financial traceability

Every metric snapshot has:

- metric name and version;
- store/date range/currency;
- formula version;
- calculated value in minor units or decimal ratio as appropriate;
- source coverage percentage;
- missing component flags;
- source freshness;
- estimated/confirmed designation;
- list of component records or query fingerprint;
- calculation trace.

A user can open estimated contribution margin and answer:

- which orders were included;
- which COGS records applied at each order date;
- which refunds/fees/ad spend were included;
- which values were missing or estimated;
- which FX rates and attribution window were used;
- when the sources last synchronized.

## 16. PII, secrets, and redaction

### 16.1 Classification

Fields are classified as:

- public;
- internal;
- customer PII;
- employee/private;
- financial-sensitive;
- secret/credential.

### 16.2 Rules

- Secret/credential values are never stored in traces, audit diffs, tool output, or logs.
- Customer PII is minimized in trace summaries and masked by role.
- Raw message bodies and attachments may be retained under a separate retention class.
- Search indexes exclude plaintext secrets and fields not needed for search.
- Exports apply the requesting user's permissions and record an audit entry.
- Deletion/anonymization preserves referential and financial integrity through stable
  pseudonymous identifiers where lawful.

## 17. Retention

Defaults are configurable per instance. A recommended baseline:

- business records: according to operational/legal need;
- action/audit ledger: long-lived, default indefinite until owner policy says otherwise;
- trace summaries: 24 months;
- detailed spans/tool payloads: 180 days;
- raw webhook payloads: 90 days unless required for reconciliation;
- raw message/attachment copies: according to inbox and privacy policy;
- operational logs: 30 days;
- failed/dead-letter payloads: 90 days or until resolved.

Retention jobs create audited deletion summaries. Deleting detail may reduce trace
coverage; the trace shows that detail expired under policy.

## 18. Integrity and tamper evidence

Within the supported application:

- immutable tables reject ordinary updates/deletes through the app role;
- state corrections append new records;
- privileged maintenance uses a separate role and creates audit records;
- payloads and document versions carry hashes;
- backups are checksummed and restore-tested.

Optional hash chaining or signed exports may provide tamper evidence. Because the owner
controls a self-hosted server and database, Ecom-OS cannot honestly promise an
owner-proof immutable ledger.

## 19. Indexing and scale

Initial indexes include:

- time and status indexes on inbox, jobs, traces, spans, actions, attempts;
- unique source-event constraints;
- entity and external-ID indexes;
- `(store_id, occurred_at)` and `(ticket_id, created_at)` composites;
- GIN indexes for selected searchable JSONB and full-text columns;
- trigram indexes for customer/order/ticket lookup where necessary;
- BRIN indexes for large append-only timestamp tables.

Partition append-only trace/event tables by month only after measured size justifies it.
Do not prematurely fragment a small single-brand database.

## 20. Replay and reconciliation

### Event replay

Replay reads immutable inbox events and re-runs a versioned projector/handler into a
controlled target. Replay never directly repeats a completed external action. Existing
action intent keys are recognized.

### Action reconciliation

Reconciliation queries provider state using the exact account and available operation
identifiers. It records new evidence and transitions the existing action; it does not
rewrite the original attempt.

### Trace repair

Late observer events or imported provider outcomes may be linked to an existing trace by
stable correlation identifiers. Automated fuzzy correlation is labeled and reviewable.

## 21. Data acceptance criteria

Before production pilot:

- every supported write produces an action and at least one trace span;
- every action can be found from its ticket/order/customer and vice versa;
- duplicate webhook and duplicate worker tests produce one business side effect;
- a connector timeout after success becomes `outcome_unknown` and later reconciles;
- trace search remains usable for a seeded 12-month dataset;
- Hermes can retrieve and compare traces through tools;
- restricted users cannot retrieve finance/founder evidence;
- secret scanning finds no plaintext credentials in database trace/audit fields;
- backup and restore preserve all cross-system identifiers;
- retention removes detail without corrupting the action ledger or entity graph.
