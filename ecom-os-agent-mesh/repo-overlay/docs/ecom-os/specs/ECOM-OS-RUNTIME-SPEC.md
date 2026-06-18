# Ecom-OS Runtime Specification

> **Status:** normative v1 integration contract  
> **Spec version:** 1.0.0  
> **Last reviewed:** 2026-06-18  
> **Tested Hermes baseline:** v0.16.0 / `v2026.6.5`

This specification defines how Ecom-OS integrates with Hermes Agent without embedding,
forking, or replacing Hermes. It is intentionally narrower than the complete Hermes
feature set. Anything not described here remains a native Hermes concern unless an ADR
adds a supported Ecom-OS integration.

Normative terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used in
the RFC sense.

## 1. Runtime goals

The integration MUST provide:

1. a Hermes-native main chat in the Ecom-OS dashboard;
2. durable background Hermes runs for ticket, research, and briefing workflows;
3. Ecom-OS ecommerce tools available to Hermes through supported extension protocols;
4. end-to-end correlation from Hermes session/run to Ecom-OS trace, tool invocation,
   action, connector attempt, and business outcome;
5. native Hermes channel and cron delivery for daily briefs and alerts;
6. owner-controlled autonomy, including unrestricted grants;
7. graceful degradation when either peer is unavailable;
8. compatibility probing rather than dependency on undocumented internals.

The integration MUST NOT:

- write directly to Hermes `state.db`;
- duplicate Hermes transcripts as a competing canonical store;
- monkey-patch Hermes core as part of the supported install;
- route browser traffic directly to a privileged Hermes endpoint;
- imply complete trace coverage for operations that bypass Ecom-OS tools;
- require Ecom-OS to own Hermes model-provider keys;
- require a separate vector database for v1.

## 2. Runtime components

### 2.1 Hermes Agent

The dedicated primary Hermes profile owns:

- agent execution and model/provider selection;
- session creation, history, lineage, and search;
- native memory and user memory;
- skills, SOUL, and agent configuration;
- delegation/subagents;
- native terminal, browser, code, and third-party tools installed by the owner;
- cron jobs and messaging gateway/channel delivery;
- native approvals and interactive requests.

### 2.2 `HermesBridge`

`HermesBridge` is an Ecom-OS backend module that normalizes supported Hermes transports.
It contains protocol code and correlation logic, not ecommerce business decisions.

Conceptual interface:

```python
class HermesBridge(Protocol):
    async def probe(self) -> HermesCapabilities: ...
    async def health(self) -> HermesHealth: ...

    async def create_session(self, request: CreateSession) -> HermesSessionRef: ...
    async def list_sessions(self, query: SessionQuery) -> Page[HermesSessionSummary]: ...
    async def get_history(self, ref: HermesSessionRef) -> HermesHistory: ...
    async def get_status(self, ref: HermesSessionRef) -> HermesSessionStatus: ...
    async def submit_prompt(self, request: InteractivePrompt) -> AsyncIterator[HermesEvent]: ...
    async def steer(self, request: SteerRequest) -> None: ...
    async def interrupt(self, request: InterruptRequest) -> None: ...
    async def branch(self, request: BranchRequest) -> HermesSessionRef: ...
    async def respond_interaction(self, response: InteractionResponse) -> None: ...

    async def start_run(self, request: BackgroundRunRequest) -> HermesRunRef: ...
    async def stream_run(self, ref: HermesRunRef) -> AsyncIterator[HermesEvent]: ...
    async def get_run(self, ref: HermesRunRef) -> HermesRunStatus: ...
    async def stop_run(self, ref: HermesRunRef) -> None: ...
    async def resolve_run_approval(self, response: RunApprovalResponse) -> None: ...
```

All concrete transport details remain behind this interface. Domain code receives typed
runtime events and references.

### 2.3 Hermes integration adapter

The preferred Hermes-side adapter is a thin, versioned extension installed using a
supported Hermes plugin/tool mechanism. It MAY provide:

- proxy registrations for the Ecom-OS tool catalog;
- lifecycle telemetry from documented plugin/gateway hooks;
- available profile, session, turn, platform, model, and tool-call context;
- optional slash commands such as `/ecom`, `/trace`, `/ticket`, and `/brief`;
- a capability/version report;
- an authenticated call to the Ecom-OS tool endpoint.

It MUST NOT contain ecommerce state machines, policy logic, connector credentials, or a
second trace database. Its network credential MUST be scoped to one Ecom-OS instance and
one Hermes profile.

### 2.4 Ecom-OS MCP server

Ecom-OS MUST expose the same core tool semantics over remote HTTP MCP as a portable
fallback. MCP tool names, argument schemas, result envelopes, versions, and risk metadata
are generated from the canonical Ecom-OS tool catalog.

The Hermes MCP configuration SHOULD include an explicit allowlist. Discovery of a tool
MUST NOT automatically grant business authorization.

### 2.5 Ecom-OS trace ingest

Adapter/hook telemetry and Hermes run events enter an authenticated, idempotent trace
endpoint. The endpoint writes the raw safe envelope to the durable event inbox before
asynchronous processing.

Observer telemetry is not the sole source of truth for Ecom-OS actions. An Ecom-OS tool
handler records its own invocation and action transactionally.

## 3. Compatibility and feature negotiation

### 3.1 Compatibility record

At startup and after every upgrade, Ecom-OS MUST record:

- exact Hermes version/build where exposed;
- active profile identity and state path fingerprint, without secrets;
- enabled programmatic transports;
- Hermes API capabilities response;
- adapter name/version/build/schema hash;
- Ecom-OS MCP catalog version/schema hash;
- available lifecycle hooks used by the adapter;
- configured native channels and cron availability at a safe metadata level;
- conformance-suite result and timestamp.

### 3.2 Required feature flags

The v1 capability model includes at least:

```text
interactive.json_rpc
interactive.session_create
interactive.session_resume
interactive.session_history
interactive.streaming
interactive.tool_events
interactive.interrupt
interactive.branch
interactive.approval_response
background.runs
background.events
background.stop
background.approval_response
external_tools.adapter
external_tools.mcp
telemetry.tool_hooks
telemetry.session_hooks
channels.delivery
cron.scheduling
```

Each product surface declares its required flags. A missing optional flag degrades only
that surface. A missing mandatory flag prevents that feature from entering ready state.

### 3.3 Capability probe behavior

The probe MUST use supported health/capability endpoints and a harmless conformance run.
Version-string comparison alone is insufficient. The probe MUST NOT create a real store
side effect.

A passing probe proves only the tested contract. It does not imply every native Hermes
extension or model provider is supported.

## 4. Interactive main chat transport

### 4.1 Selected protocol

The Ecom-OS main chat SHOULD use Hermes TUI Gateway JSON-RPC over a backend-controlled
WebSocket or supervised stdio process. The documented protocol supports fine-grained
session operations, streamed message/tool events, interactive approval/clarification,
interrupt, branching, compression, and slash commands.

The browser connects to an authenticated Ecom-OS WebSocket endpoint. Ecom-OS:

1. authenticates and authorizes the human;
2. resolves the allowed Hermes profile;
3. creates or resumes a bridge connection;
4. translates browser commands to allowed JSON-RPC methods;
5. validates and normalizes streamed events;
6. persists Ecom-OS trace linkage;
7. forwards safe UI events to the browser.

The browser MUST NOT receive a generic `cli.exec`, `config.set`, `reload.env`,
`process.stop`, secret-response, or service-level Hermes credential merely because those
methods exist in the upstream protocol. Ecom-OS exposes only product-approved methods in
its web client. The owner remains able to use native Hermes interfaces separately.

### 4.2 Supported interactive operations

V1 MUST support:

- create session;
- list/resume saved sessions;
- retrieve visible history;
- submit prompt;
- receive message deltas and final messages;
- display tool start/progress/result;
- display and resolve clarification and Ecom-OS-safe approval requests;
- interrupt current work;
- display session status and usage where available;
- branch a session;
- link/unlink business entities to the session;
- open the Ecom-OS trace drawer from a tool event.

V1 MAY support:

- session steering;
- compression;
- model switching subject to user role and Hermes policy;
- image attachment;
- delegation tree display;
- selected slash commands.

### 4.3 Session persistence

Hermes session IDs are canonical. Ecom-OS stores a reference and derived metadata only:

- Hermes profile ID;
- Hermes session ID/key;
- source/platform;
- Ecom-OS user/channel identity;
- title cache;
- last-seen timestamp;
- linked Ecom-OS entities;
- trace/run links;
- access label.

Ecom-OS MUST retrieve transcript content through supported Hermes session operations. It
MAY maintain a short-lived UI cache, but a cache entry declares source and age and is not
used as canonical history.

### 4.4 Chat-to-trace lifecycle

For every submitted Ecom-OS dashboard prompt:

1. create an Ecom-OS `trace` of type `chat_turn` before forwarding;
2. create an Ecom-OS `run` with the known Hermes session reference;
3. attach `trace_id` to adapter context where the supported transport permits;
4. stream Hermes events into spans with honest coverage;
5. link all Ecom-OS tool invocations through propagated context or reconciliation;
6. close the run on final, interrupt, transport failure, or timeout;
7. keep the trace open while child actions or reconciliation remain pending;
8. make the trace discoverable from the chat message and Activity page.

Ecom-OS stores visible prompt/output references and safe event metadata. It MUST NOT
require or expose private hidden chain-of-thought.

### 4.5 Interactive requests and approvals

Hermes-native approval, clarification, sudo, and secret requests are distinct event types.
The Ecom-OS UI MUST NOT collapse them into one generic “Approve” button.

- **Clarification:** may be answered by the active user.
- **Ecom-OS action approval:** resolves an Ecom-OS approval bound to an exact action
  digest; the response may then allow the waiting tool call/run to continue.
- **Native Hermes tool approval:** MAY be surfaced when supported, clearly labeled as a
  Hermes approval with its native scope.
- **Sudo/secret request:** MUST NOT be accepted through the ordinary Ecom-OS browser in
  v1 unless a later audited design explicitly supports secure entry. Use native Hermes
  administration instead.

## 5. Background run transport

### 5.1 Selected protocol

Ecom-OS-triggered agent jobs SHOULD use the Hermes API server asynchronous run interface:

- create a run;
- store the returned run ID and session headers/references;
- consume the lifecycle event stream;
- poll status as a recovery path;
- resolve supported approvals;
- stop runs on cancellation or lease loss.

A background run is always initiated from a durable Ecom-OS job. The HTTP request itself
is not the queue.

### 5.2 Background run request

The normalized request includes:

```json
{
  "ecom_trace_id": "trc_...",
  "ecom_job_id": "job_...",
  "workflow": "ticket_triage.v1",
  "hermes_profile_id": "hp_...",
  "session_strategy": "new|resume_entity|resume_explicit",
  "hermes_session_ref": "optional",
  "prompt": "rendered visible task prompt",
  "entity_refs": [{"type": "ticket", "id": "tkt_..."}],
  "requested_tools": ["ecom.ticket.get", "ecom.order.get"],
  "deadline_at": "...",
  "initiator": {"type": "event|human|cron", "id": "..."}
}
```

The exact Hermes request encoding is transport-specific. Ecom-OS stores the normalized
request and hashes the rendered prompt/configuration used for the run.

### 5.3 Run ownership and leases

The worker that starts a run holds a renewable job lease. Losing the lease does not
immediately start a duplicate run. A recovery worker first queries the known Hermes run
and session status. Only when the prior run is proven absent/terminal may it create a new
attempt.

Each workflow defines:

- maximum wall time;
- maximum attempts;
- retryable transport/provider errors;
- whether the same Hermes session is resumed;
- escalation behavior;
- external-write eligibility;
- reconciliation behavior after interruption.

### 5.4 Event-stream recovery

SSE/WebSocket disconnection does not imply run failure. Ecom-OS reconnects or polls the
run status and reconciles adapter telemetry. Missing observer events create a trace-gap
record; they do not delete known actions/tool calls.

## 6. Tool catalog contract

### 6.1 Canonical definition

Every Ecom-OS tool is defined once in a versioned catalog. The catalog generates:

- adapter registration schema;
- MCP schema;
- server validation model;
- UI documentation;
- risk/autonomy metadata;
- conformance fixtures;
- compatibility hash.

Required tool metadata:

```text
name
version
description
input_schema
output_schema
read_or_write
risk_class
required_ecom_permissions
required_connection_types
store_scope_rule
supports_simulation
supports_idempotency
reconciliation_strategy
sensitive_fields
minimum_trace_coverage
```

Tool names use stable namespaces, for example:

```text
ecom.store.list
ecom.ticket.search
ecom.ticket.get
ecom.ticket.propose_reply
ecom.ticket.send_reply
ecom.order.search
ecom.order.get
ecom.customer.get
ecom.discount.create
ecom.refund.propose
ecom.refund.execute
ecom.task.create
ecom.metric.get
ecom.trace.search
ecom.trace.get
ecom.incident.create
ecom.daily_brief.get
ecom.document.search
```

A write tool MUST be explicit. A read tool named `order.get` must never opportunistically
update the order.

### 6.2 Invocation envelope

Adapter and MCP transports normalize into:

```json
{
  "invocation_id": "inv_...",
  "tool_name": "ecom.ticket.send_reply",
  "tool_version": "1.0.0",
  "schema_hash": "sha256:...",
  "arguments": {},
  "context": {
    "trace_id": "trc_...",
    "run_id": "run_...",
    "hermes_profile_id": "hp_...",
    "hermes_session_id": "...",
    "hermes_run_id": "...",
    "hermes_tool_call_id": "...",
    "source_platform": "dashboard|telegram|slack|...",
    "ecom_user_id": "optional",
    "channel_identity_id": "optional",
    "store_id": "required when scoped",
    "connection_id": "required for a write"
  }
}
```

Some Hermes fields may be unavailable on a given transport. Missing fields MUST remain
null/absent rather than fabricated. The server resolves the effective identity and scope
from authenticated service/human/channel context and stored mappings; it does not trust
arbitrary client-supplied role names.

### 6.3 Result envelope

Every tool returns a machine-readable result:

```json
{
  "ok": true,
  "status": "completed|proposed|awaiting_approval|queued|degraded|failed",
  "trace_id": "trc_...",
  "invocation_id": "inv_...",
  "action_id": "optional",
  "approval_id": "optional",
  "data": {},
  "evidence": [{"type": "...", "id": "..."}],
  "freshness": {"as_of": "...", "status": "current|stale|partial"},
  "warnings": [],
  "error": null
}
```

Failures use stable error codes and safe messages. A tool never returns a plaintext
secret. Human-readable text MAY accompany structured data but cannot be the only signal
for approval, action state, or freshness.

### 6.4 Read tools

Read tools MUST:

- enforce effective identity and access labels;
- identify store and source;
- include freshness/coverage for live operational data;
- return evidence references;
- distinguish not-found, inaccessible, unavailable, and stale;
- avoid side effects beyond trace/audit and safe cache refresh explicitly declared in
  metadata.

### 6.5 Write tools

Write tools MUST:

1. validate the current catalog/schema version;
2. authenticate the invoking service and effective actor;
3. resolve exact brand/store/connection/entity scope;
4. create the tool invocation record;
5. normalize arguments and derive an action digest/intent key;
6. resolve the effective grant/autonomy mode;
7. evaluate policy or approval where selected;
8. re-read state-sensitive current data before authorization/execution;
9. create or reuse one durable action;
10. execute through the connector adapter;
11. record every attempt and provider reference;
12. reconcile ambiguous outcomes before dangerous retries;
13. return trace/action state.

The LLM may choose arguments. The action executor preserves exactly which arguments and
state were used; it does not claim the choice was correct.

## 7. Correlation and trace coverage

### 7.1 Correlation sources

Correlation is established using, in priority order:

1. Ecom-OS `trace_id` explicitly propagated into adapter invocation context;
2. Ecom-OS background `run_id`/Hermes run linkage;
3. Hermes session ID + native tool-call ID;
4. adapter-generated invocation ID returned by Ecom-OS;
5. time-bounded reconciliation using session, tool name, argument fingerprint, and actor;
6. observer-only import when no stronger link is available.

A reconciled link records method and confidence. It never silently upgrades evidence
quality.

### 7.2 Coverage rules

- An Ecom-OS tool invocation handled by the authenticated Ecom-OS endpoint is `verified`.
- An Ecom-OS action and its attempts are `verified` even if upstream outcome remains
  `unknown`.
- A Hermes hook reporting a native terminal/browser/tool call is normally `observed`.
- An upstream webhook revealing an action performed elsewhere is `imported`.
- Missing or contradictory evidence is `unknown`.

A trace summary MUST show both completion status and coverage. “Succeeded” does not mean
“fully observed,” and “verified” does not mean “good decision.”

### 7.3 Trace-access tools

Hermes MUST receive read-only tools that can:

- search traces by date, ticket, order, customer, action, tool, status, actor, or error;
- retrieve a trace timeline;
- retrieve redacted tool inputs/results and evidence;
- compare active prompt/skill/policy/config versions to a historical run;
- identify actions with unknown outcomes;
- open an incident or add an analysis note subject to identity permissions.

These tools enable “inspect what went wrong last Tuesday” without giving the agent direct
SQL or raw-secret access.

## 8. Autonomy resolution

### 8.1 Grant model

A grant is scoped by:

- grantee: Hermes profile/agent role, service identity, human role, or channel identity;
- tool/tool group and version range;
- brand/store/connection/entity constraints;
- mode: `disabled`, `observe`, `approve`, `policy`, or `unrestricted`;
- optional schedule and expiry;
- optional policy reference;
- creator and audited reason.

Resolution uses the most specific applicable grant. Deny/disabled wins over broader
allows unless an explicit owner-level override record states otherwise. The final rule
and resolution path are stored on the tool invocation/action.

### 8.2 Mode semantics

| Mode | Read/propose | External write | Business policy/cap | Human approval |
|---|---:|---:|---:|---:|
| `disabled` | no | no | n/a | n/a |
| `observe` | yes | no; simulate/propose only | may explain | no execution |
| `approve` | yes | after exact approval | optional precheck | required |
| `policy` | yes | when policy passes | required | only when policy says |
| `unrestricted` | yes | yes | bypassed | bypassed |

Technical-integrity checks always apply.

### 8.3 Approval binding

An Ecom-OS approval MUST bind to:

- action ID and action digest;
- action type/tool version;
- exact normalized arguments;
- exact store/connection/target;
- amount/currency where applicable;
- requesting actor/run;
- current-state fingerprint or validation requirements;
- expiry;
- approver scope.

Changing any bound field invalidates the approval. At execution time, current-state rules
may still make an approved action stale or impossible; the action returns for review
rather than mutating the approved intent.

### 8.4 Unrestricted semantics

`unrestricted` means Ecom-OS does not impose business caps or require an Ecom-OS human
approval for the granted capability and scope. It does not mean:

- anonymous access;
- automatic account selection;
- arbitrary schema bypass;
- duplicate execution;
- secret disclosure;
- pretending an unknown connector outcome failed;
- execution against a disconnected or invalid account;
- suppression of trace/audit records.

## 9. Memory and knowledge contract

### 9.1 Hermes-native memory

Hermes built-in curated memory and user memory remain native. Ecom-OS MAY provide skills
that teach Hermes when to remember operator preferences or stable brand facts. Ecom-OS
MUST NOT write directly to memory files or SQLite behind Hermes's back.

Native memory is suitable for compact durable guidance and preferences. It is not the
canonical location for current orders, ticket states, financial calculations, action
outcomes, access-controlled founder documents, or large source corpora.

### 9.2 Session search

Hermes session search/history is used to retrieve prior conversations. Ecom-OS stores
session references so a trace or entity page can open the relevant native history.

Ecom-OS MUST NOT rely on session text as proof that an external action succeeded; the
action ledger/provider evidence is authoritative.

### 9.3 Operational retrieval

Current data is exposed through Ecom-OS read tools. Results include source, freshness,
coverage, and evidence. Structured retrieval is preferred to injecting large business
snapshots into every system prompt.

### 9.4 Documents and SOPs

Source documents live in the user-space vault and are indexed by Ecom-OS. Hermes may
retrieve them through `ecom.document.search/get`. Access control is applied before
content enters model context.

Postgres full-text search is the v1 baseline. Optional semantic providers remain additive
and must preserve document version, provenance, access label, and source link.

## 10. Profiles and delegation

One primary Hermes profile is the default brand brain. Additional profiles MAY be used
for isolation, experimentation, or specialized channels, but each is explicit and has a
separate compatibility/identity record.

A Hermes profile is a state/configuration boundary, not a process sandbox. Ecom-OS does
not base a security guarantee solely on profile separation.

Delegated/subagent work:

- remains native Hermes behavior;
- inherits or resolves Ecom-OS tool identity through available session/run context;
- cannot gain an Ecom-OS tool grant merely by being spawned;
- is represented as nested/linked runs when telemetry permits;
- receives honest trace coverage when context is incomplete.

The owner may deliberately grant broad tools to a delegated agent. The effective grant
is recorded at invocation time.

## 11. Customer-service runtime

### 11.1 Ticket trigger

A ticket workflow begins only from a normalized durable event. The worker obtains a
per-ticket ordering lock/lease and re-reads current ticket state.

### 11.2 State machine

Minimum states:

```text
open
  → queued_for_agent
  → agent_running
  → proposed
  → awaiting_approval | ready_to_send | needs_rep
  → sending
  → sent
  → waiting_customer
  → resolved

any active state → needs_rep
connector ambiguity → outcome_unknown
```

Customer replies to `needs_rep` append and notify; they do not automatically resume the
same autonomous workflow unless the configured owner policy explicitly reopens it. The
chosen policy and trigger are traced.

### 11.3 Run context

The ticket run prompt contains only the task, trusted operating instructions, and
references necessary to retrieve current data. Customer content is clearly marked as
untrusted evidence. The run is encouraged to use read tools before proposing an action,
but correctness depends on tool/action controls rather than prompt wording alone.

### 11.4 Reply execution

A final outbound reply is an Ecom-OS action linked to:

- triggering inbound message;
- exact final body hash;
- ticket/channel/recipient;
- language/template/skill versions where available;
- supporting order/evidence;
- grant/autonomy/policy/approval;
- connector attempt and provider message ID.

The intent key prevents sending the same final reply twice for the same inbound trigger.
A changed body is a new proposed action and may require new approval.

### 11.5 Shadow and autonomy stages

Production rollout supports:

1. `observe`: classify and draft only;
2. `approve`: human sends/approves every reply;
3. `policy`: configured classes send automatically;
4. `unrestricted`: all granted reply/action tools execute without business approval.

The owner can skip stages, but the UI records the choice and preserves comparable quality
metrics.

## 12. Native channels and daily brief

### 12.1 Channel ownership

Hermes gateway owns Telegram, Slack, Discord, email, and other supported operator channel
connections. Ecom-OS does not reimplement these transports.

Ecom-OS provides:

- identity mappings;
- brief/alert content and structured source data;
- Ecom-OS tools callable from channel conversations;
- delivery intent and trace records;
- status callbacks/imported delivery evidence where available.

### 12.2 Daily brief generation

A daily brief has two stages:

1. **Deterministic snapshot:** Ecom-OS computes metrics and queues from a fixed cutoff,
   including freshness, coverage, currency, and links.
2. **Optional Hermes narration:** Hermes summarizes and prioritizes the snapshot using a
   visible prompt/skill version.

If Hermes or the model is unavailable, Ecom-OS produces a deterministic fallback message.
Numbers MUST never be invented by the narration stage.

Default sections:

- yesterday's estimated contribution margin and revenue context;
- advertising spend/ROAS with attribution caveat;
- ticket volumes, autonomous replies, escalations, reopen rate, and oldest backlog;
- external actions by type and any failures/unknown outcomes;
- tasks due today and overdue;
- research/insights completed;
- incidents, connection health, stale data, and trace gaps;
- prioritized links into Ecom-OS.

### 12.3 Scheduling and delivery

The owner MAY schedule the brief using Hermes cron so it arrives through the native home
channel. The cron task calls or retrieves `ecom.daily_brief.generate/get`, then delivers
through native Hermes messaging.

Ecom-OS records:

- brief window/timezone;
- snapshot ID and component evidence;
- Hermes session/run/cron reference when available;
- final rendered body hash;
- target platform/channel mapping;
- delivery intent/status/evidence;
- trace and any failure.

Repeated delivery uses a brief/date/channel idempotency key.

## 13. Failure behavior

### 13.1 Hermes unavailable

- Ecom-OS structured pages and deterministic calculations remain available.
- New agent runs remain queued or escalate according to workflow.
- Main chat clearly reports Hermes unavailable.
- Existing Ecom-OS action reconciliation continues.
- Deterministic daily brief fallback MAY still be delivered only if a non-Hermes delivery
  path was explicitly configured; otherwise delivery waits and alerts.

### 13.2 Ecom-OS unavailable

- Native Hermes remains available for non-Ecom work.
- Ecom-OS tools return a bounded unavailable error; they do not hang indefinitely.
- The adapter buffers only a small bounded amount of non-sensitive telemetry, if at all;
  it is not an alternate action queue.
- No Ecom-OS write is accepted in memory only.

### 13.3 Transport interruption

- Interactive UI reconnects and queries current session status/history.
- Background worker polls known run status before retrying.
- Tool invocation/action records already accepted by Ecom-OS remain authoritative.
- Duplicate telemetry is idempotently ignored.

### 13.4 Schema mismatch

A tool schema hash/version mismatch fails before domain execution and emits an actionable
compatibility error. It must never “best effort” reinterpret a money-touching argument.

## 14. Security requirements

- All peer-to-peer calls are authenticated and use TLS or a private trusted host socket.
- Service credentials are rotatable and audience-scoped.
- Tool context supplied by Hermes is treated as asserted metadata until mapped to an
  authenticated Ecom-OS identity.
- Customer, supplier, document, and web content cannot alter grants, credentials, or
  integration configuration through data fields.
- Raw secrets are neither arguments nor results of general Ecom-OS tools.
- Access-controlled data is filtered before return to Hermes.
- Ecom-OS action approvals cannot be satisfied by untrusted message text.
- Tool output is size-bounded and structured to limit accidental context flooding.
- Adapter/plugin updates are explicit and compatibility-checked.

## 15. Conformance suite

A Hermes/Ecom-OS combination is supported only when the applicable suite passes.

### 15.1 Protocol tests

- create, list, resume, and retrieve a session;
- submit a prompt and receive ordered streamed events;
- interrupt a run;
- branch a session;
- surface one clarification or harmless approval flow;
- create a background run, consume events, query completion, and stop a long test run;
- detect a deliberate transport disconnect and recover status.

### 15.2 Tool tests

- discover the expected adapter/MCP tool catalog and schema hash;
- call a read tool and correlate session/run/tool invocation/trace;
- reject an unknown tool version;
- reject forged user/store/connection context;
- prove an adapter/MCP duplicate maps to one invocation/action intent;
- prove a write simulation produces no provider side effect;
- verify secrets are absent from result/log/trace exports.

### 15.3 Trace tests

- every dashboard chat turn creates a linked trace/run;
- every Ecom-OS tool call is `verified` and searchable;
- native Hermes-only test activity is not mislabeled `verified`;
- a dropped hook event creates/reconciles a coverage gap without losing the action;
- trace tools can find a seeded ticket/action incident.

### 15.4 Autonomy tests

For the same action fixture:

- `disabled` rejects;
- `observe` simulates/proposes;
- `approve` waits for exact digest and rejects modified/expired approval;
- `policy` follows the versioned policy result;
- `unrestricted` executes without business cap/approval;
- every mode still rejects wrong-account, malformed, and duplicate intent.

### 15.5 Channel and cron tests

- mapped and unmapped channel identities resolve correctly;
- a test brief is generated from deterministic data;
- native Hermes scheduling/delivery succeeds where configured;
- repeated delivery does not duplicate the same brief;
- delivery failure is visible and retryable.

### 15.6 Gate

Failure of a required conformance test sets the dependent feature to `not_ready`. The
operator may use unrelated features, but the production UI must not silently enable a
workflow whose integration contract failed.

## 16. Acceptance scenarios

The runtime is v1-ready when the following complete end-to-end:

1. **Ask anything:** A user opens an existing Hermes session in Ecom-OS, asks for a ticket
   and order explanation, Hermes calls Ecom-OS read tools, and the answer links to a
   verified trace and evidence.
2. **Ticket in shadow mode:** A duplicate-delivered inbound WISMO message creates one
   ticket trigger, one Hermes run, one draft, and no outbound action.
3. **Approved reply:** A representative approves an exact reply, one connector message is
   sent, the provider ID is recorded, and a replay sends nothing.
4. **Unrestricted reply:** The owner grants unrestricted reply capability; a qualifying
   run sends without approval while retaining all trace/action records.
5. **Ambiguous outcome:** The connector times out after receiving a request; the action
   becomes `outcome_unknown`, reconciliation finds the provider message, and no duplicate
   is sent.
6. **Historical diagnosis:** The owner asks Hermes to inspect a bad interaction from a
   date range; Hermes retrieves the trace, prompt/skill/policy versions, tool arguments,
   evidence, and action outcome and creates an incident note.
7. **Daily brief:** A deterministic prior-day snapshot is narrated by Hermes and delivered
   through the configured native channel with links; a second execution does not deliver
   twice.
8. **Peer outage:** Hermes is stopped; Ecom-OS pages and action reconciliation remain
   usable, agent work pauses visibly, and work resumes without duplicate runs after
   Hermes returns.

## 17. Upstream references

The tested contract is based on the official Hermes Agent documentation:

- [Release history](https://github.com/NousResearch/hermes-agent/releases)
- [Programmatic integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration)
- [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)
- [Session storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage)
- [Persistent memory and session search](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [MCP integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)
- [Scheduled tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [Messaging gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)
- [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Webhooks](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks)

The repository compatibility matrix MUST pin concrete upstream versions and record any
behavioral deviations found by the conformance suite. Documentation describes the
intended upstream contract; the local capability probe remains the final production gate.
