# 01 — Architecture

> **Status:** normative system shape  
> **Last reviewed:** 2026-06-18  
> **Hermes baseline:** v0.16.0 / `v2026.6.5`

## 1. Architectural intent

Ecom-OS and Hermes Agent are peer systems with a deliberately narrow integration
boundary.

- **Hermes owns agent behavior:** sessions, conversation history, model execution,
  memory, skills, delegation, cron, approvals, and messaging channels.
- **Ecom-OS owns ecommerce operations:** normalized business data, queues, tickets,
  metrics, tasks, policies, approvals for Ecom-OS actions, connector execution, traces,
  incidents, and dashboards.
- **The integration layer translates between them:** Hermes can use Ecom-OS as native
  tools, and Ecom-OS can host Hermes conversations without replacing Hermes.

This separation lets each product update independently, keeps live business state out of
prompt files, and avoids coupling Ecom-OS to private Hermes implementation details.

## 2. System context

```text
Human operators
   │
   ├── Ecom-OS web app ───────────────────────────────────────────┐
   │       │                                                      │
   │       ├── structured pages                                  │
   │       └── Hermes-native main chat                            │
   │                                                              │
   └── Hermes native channels                                     │
           Telegram / Slack / Discord / email / ...                │
                    │                                              │
                    ▼                                              │
          ┌─────────────────────┐                                  │
          │ Hermes Agent        │                                  │
          │ dedicated profile   │                                  │
          │                     │                                  │
          │ sessions + state.db │                                  │
          │ memory + skills     │                                  │
          │ cron + gateway      │                                  │
          │ native tools        │                                  │
          └───────┬─────────────┘                                  │
                  │ official integration surfaces                  │
                  │ JSON-RPC / HTTP+SSE / plugin hooks / MCP       │
                  ▼                                                │
          ┌─────────────────────┐        ┌──────────────────────┐  │
          │ Hermes integration  │        │ Ecom-OS API          │◄─┘
          │ adapter             │───────►│ auth + domain logic  │
          │ thin, replaceable   │        │ action executor      │
          └─────────────────────┘        │ trace ingest         │
                                         └──────────┬───────────┘
                                                    │
                              ┌─────────────────────┼──────────────────┐
                              ▼                     ▼                  ▼
                      ┌─────────────┐       ┌──────────────┐   ┌──────────────┐
                      │ Postgres    │       │ Worker       │   │ Connector     │
                      │ truth +     │       │ durable jobs │   │ adapters      │
                      │ traces      │       │ + sync       │   │               │
                      └─────────────┘       └──────────────┘   └──────┬───────┘
                                                                       │
                                        Shopify / inbox / ads / payments /
                                        suppliers / Composio / direct APIs
```

## 3. Deployment unit

The supported production topology is one brand per Ecom-OS deployment and one dedicated
primary Hermes profile for that brand.

A typical Docker Compose or systemd deployment contains:

- `ecom-web` — Next.js user interface;
- `ecom-api` — authenticated HTTP/WebSocket API;
- `ecom-worker` — durable event, synchronization, reconciliation, and scheduled jobs;
- `postgres` — canonical Ecom-OS database and durable queue;
- `hermes-gateway` — the brand's Hermes profile and native channels;
- optional connector-side services required by the selected adapters;
- a reverse proxy terminating TLS.

Hermes may run in its own container or as a host service. It must expose supported local
integration endpoints to `ecom-api`, not directly to the public browser.

A single instance may connect multiple storefronts for the same brand later. Every event,
tool call, and action remains explicitly bound to one `store_id` and one connection.

## 4. Core boundaries

### 4.1 Ecom-OS core

Ecom-OS core includes:

- identity and role management;
- data ingestion and normalization;
- ecommerce domain models;
- connector adapter contracts;
- the durable event inbox and outbox;
- the trace and action ledger;
- tool schemas and tool handlers;
- autonomy policies and approvals;
- background jobs and reconciliation;
- the Hermes bridge;
- the web application and design system;
- the Ecom-OS extension host.

### 4.2 Hermes runtime

Hermes remains an independently installed and versioned dependency. Ecom-OS does not:

- vendor or patch Hermes core;
- write directly to Hermes `state.db`;
- implement a competing memory store for ordinary Hermes memory;
- recreate Hermes channel adapters;
- recreate Hermes cron semantics;
- duplicate Hermes chat transcripts as a second canonical history;
- assume undocumented Python internals are stable.

Ecom-OS may back up Hermes profile files and may cache derived session metadata for UI
search. The canonical session content remains Hermes-owned.

### 4.3 Integration adapter

The Hermes-side integration adapter is a thin package installed through supported Hermes
extension mechanisms. It is not the Ecom-OS application and contains no authoritative
business state.

Its responsibilities are limited to:

- registering Ecom-OS proxy tools and/or configuring the Ecom-OS MCP server;
- forwarding supported lifecycle and tool telemetry to Ecom-OS;
- attaching available session, turn, task, profile, model, and platform identifiers;
- registering optional Ecom-OS slash commands;
- reporting adapter and Hermes capability information;
- failing open for unrelated Hermes work when Ecom-OS is unavailable, while clearly
  failing Ecom-OS tool calls.

The adapter authenticates to Ecom-OS with a rotatable machine credential scoped to one
instance and profile.

## 5. Supported Hermes integration surfaces

Ecom-OS uses documented Hermes interfaces in preference order by use case.

### 5.1 Interactive dashboard chat

The main chat uses the Hermes TUI Gateway JSON-RPC protocol over a backend-controlled
stdio or WebSocket connection because it exposes:

- session creation and resume;
- history and status;
- streamed message deltas;
- tool start/progress/complete events;
- clarification and approval requests;
- cancellation, steering, branching, and compression;
- slash command dispatch and model switching.

The browser never receives the raw Hermes API key. `ecom-api` authenticates the user,
proxies the protocol, and links Hermes events to Ecom-OS trace IDs.

### 5.2 Background agent runs

Ticket processing, research jobs, and other Ecom-OS-triggered runs use Hermes's HTTP API
server and asynchronous run/event endpoints when available. The Ecom-OS worker:

1. creates a run with an explicit Hermes session key;
2. records the returned run/session identifiers;
3. consumes the event stream;
4. resolves approval requests when the Ecom-OS policy requires it;
5. persists completion, failure, interruption, and cost metadata;
6. reconciles the run against adapter telemetry.

Hermes webhooks may be used for owner-configured event activation, but Ecom-OS's durable
inbox remains the source of truth for ecommerce events.

### 5.3 Ecommerce tools

Two supported tool transports expose the same versioned Ecom-OS tool contract:

1. **Hermes integration adapter tools — preferred for full trace correlation.** A thin
   Hermes plugin registers proxy tools whose handlers call Ecom-OS. Supported Hermes
   context identifiers are forwarded with every invocation.
2. **Remote HTTP MCP server — portable fallback and third-party compatibility.** Hermes
   discovers tools through MCP with an explicit include list. This path may provide less
   Hermes-specific correlation, so trace coverage is labeled accordingly.

Tool semantics live in Ecom-OS. The adapter and MCP server are transports, not separate
business implementations.

### 5.4 Lifecycle telemetry

The adapter uses documented Hermes plugin and gateway hooks to observe sessions, turns,
model calls, tool calls, approvals, resets, and finalization where those events are
available. Ecom-OS never assumes hook delivery is durable. Telemetry is:

- signed;
- assigned a deterministic event identity where possible;
- accepted into a durable inbox;
- idempotently processed;
- reconciled with Ecom-OS tool/action records.

Loss of an observer event must not lose an Ecom-OS action record because Ecom-OS tool
handlers record their own invocation and result transactionally.

### 5.5 Native channels and scheduled delivery

Operator messaging remains in the Hermes gateway. Ecom-OS stores mappings between:

- an Ecom-OS user;
- a Hermes profile;
- a platform;
- a platform user/chat/channel identifier;
- a role and allowed Ecom-OS tool scope.

Daily briefs and alerts use Hermes cron, `send_message`, or `hermes send`. Ecom-OS stores
the brief and delivery trace even when the resulting message is not part of an ordinary
interactive channel transcript.

## 6. Canonical state ownership

| Domain | Canonical owner | Access path |
|---|---|---|
| Hermes sessions and messages | Hermes SQLite and Hermes APIs | JSON-RPC/API/session search |
| Hermes memory and user profile | Hermes `MEMORY.md` / `USER.md` | Native Hermes memory tools |
| Hermes skills, SOUL, cron, gateway config | Hermes profile | Native Hermes management |
| Store, order, customer, product, ticket state | Ecom-OS/Postgres and upstream reconciliation | Ecom-OS tools/API |
| Financial metrics and source coverage | Ecom-OS/Postgres | Ecom-OS metrics tools/API |
| Agent run linkage and operational traces | Ecom-OS/Postgres | Trace API/tools |
| External action state | Ecom-OS action ledger plus provider reconciliation | Action API/tools |
| Business policies and autonomy settings | Ecom-OS/Postgres | Settings/API/tools |
| Documents and SOP source files | User-space vault | Document service/Ecom-OS tools |
| Credentials | Hermes profile, connector provider, or secret store as appropriate | Never returned through tools |

No component should maintain a silent second authoritative copy. Derived caches declare
their source and refresh time.

## 7. Memory and knowledge architecture

The design uses Hermes-native capabilities first and does not require an external vector
database.

### 7.1 Hermes-native knowledge

The primary Hermes profile owns:

- bounded curated memory for durable preferences and lessons;
- full SQLite-backed session history and native session search;
- skills and SOP procedures;
- SOUL/personality and context files;
- optional Hermes memory-provider integration chosen by the owner.

### 7.2 Ecom-OS operational knowledge

Live business facts remain structured and are retrieved through tools. Examples:

- current order and fulfilment state;
- customer history;
- ticket status and ownership;
- product and supplier information;
- current policy version;
- action and incident history;
- contribution-margin inputs;
- tasks and approvals.

### 7.3 Document vault

Long-form brand documents live in a user-space document vault. Ecom-OS stores metadata,
versions, access labels, checksums, and ingestion status. V1 search uses PostgreSQL full
text and metadata filtering; an embedding index or a Hermes memory provider is optional
and additive.

Documents are never silently converted into authoritative business state. Extracted facts
retain source, timestamp, and document version.

## 8. Event-driven operational core

### 8.1 Durable event inbox

All inbound ecommerce events pass through:

```text
receive → authenticate/verify → normalize envelope → persist inbox row
       → acknowledge provider → claim job → process idempotently
       → emit domain events/outbox → project current state
```

The provider is acknowledged only after durable acceptance. Processing may happen later.
The inbox stores provider event IDs, payload hashes, source, store, occurred/received
timestamps, verification result, and processing state.

### 8.2 Postgres-backed jobs

V1 uses Postgres as the durable queue to keep the deployment small. Workers claim jobs
with row locking and leases. The job system supports:

- retries with exponential backoff and jitter;
- maximum attempts;
- lease expiry and recovery;
- dead-letter state;
- deduplication keys;
- per-store and per-entity serialization keys;
- explicit cancellation;
- trace linkage.

A separate broker may be introduced later only when measured throughput requires it.

### 8.3 Transactional outbox

Events that must leave a database transaction are first written to an outbox row in the
same transaction. Workers deliver them to Hermes, connectors, notifications, or plugins.
This prevents “database committed but message was lost” gaps.

## 9. Run, trace, and action model

A trigger creates or joins a trace. The trace contains one or more runs and spans.

```text
Trace
 ├── trigger span
 ├── context/retrieval spans
 ├── Hermes run
 │    ├── LLM call spans
 │    ├── Hermes native tool spans (observed when available)
 │    └── Ecom-OS tool invocation spans (verified)
 ├── action
 │    ├── policy/approval decision
 │    ├── connector attempt(s)
 │    └── reconciliation outcome
 └── business result / incident / follow-up task
```

Ecom-OS distinguishes trace coverage:

- **Verified:** executed by an Ecom-OS tool/action handler with durable before/after
  records.
- **Observed:** reported by a Hermes hook or protocol event, but Ecom-OS did not execute
  the underlying side effect.
- **Imported:** inferred from an upstream webhook or later synchronization.
- **Unknown:** evidence suggests an outcome, but the responsible execution path is
  outside Ecom-OS visibility.

This label is visible in the UI and returned by trace tools.

## 10. Tool and action architecture

### 10.1 Tool catalog

Every Ecom-OS tool has a versioned definition:

- stable name;
- semantic version;
- read/write/admin classification;
- JSON schema;
- required identity and store scope;
- side-effect category;
- idempotency behavior;
- supported autonomy modes;
- required connector capability;
- redaction rules;
- trace fields;
- deprecation status.

### 10.2 Effective grant

An invocation is evaluated from:

```text
human/channel identity
+ Hermes profile and agent identity
+ store scope
+ tool grant
+ autonomy mode
+ optional business policy
+ current resource state
= effective execution decision
```

The decision is stored with the invocation. The UI explains which layer allowed, paused,
or rejected it.

### 10.3 Autonomy modes

Business restrictions are owner-configurable. Technical integrity is not.

| Mode | Read | External write | Business policy | Human approval |
|---|---:|---:|---:|---:|
| Disabled | no | no | n/a | n/a |
| Observe | yes | simulate only | optional | no |
| Approve | yes | after approval | optional | always |
| Policy | yes | when policy passes | yes | on configured fallback |
| Unrestricted | yes | immediate | bypassed | no |

In every mode, Ecom-OS still requires authenticated identity, explicit store/account
binding, valid schema, durable trace creation, idempotency, secret handling, and outcome
recording.

### 10.4 Action executor

Write tools create an `action` before contacting an upstream provider. The executor:

1. freezes normalized arguments and target identity;
2. records the effective grant and policy result;
3. waits for approval when required;
4. verifies the approval is for the exact action digest;
5. checks current upstream state when the operation is state-sensitive;
6. creates an attempt with a provider idempotency key;
7. calls the selected connector;
8. records response metadata and redacted payloads;
9. marks success, failure, or outcome-unknown;
10. reconciles outcome-unknown before retrying a dangerous write;
11. emits resulting domain events.

This executor is a reliability and traceability boundary, not an immutable business-policy
cage. In unrestricted mode, steps concerning optional business policy and human approval
are skipped, while the rest remain.

## 11. Main chat architecture

The Ecom-OS chat page is a Hermes client with Ecom-OS context and navigation.

The page contains:

- Hermes session list and resume;
- streaming messages and tool progress;
- model/profile indicator;
- clarification and approval cards;
- stop, steer, branch, and retry controls;
- context chips for active store, ticket, order, customer, date range, or incident;
- linked entity cards returned by Ecom-OS tools;
- a trace drawer for the active turn;
- “inspect with Hermes” and “open in trace explorer” actions.

Ecom-OS does not insert hidden business facts into every prompt. Context chips resolve to
fresh tool-accessible entities. Small ephemeral context may be supplied for navigation,
identity, and trace correlation.

## 12. Customer-service flow

```text
Inbox/provider event
  → verified durable inbox
  → ticket/message normalization and thread resolution
  → ownership/sticky-escalation check
  → create trace and Hermes ticket run
  → Hermes retrieves ticket + order + policy through tools
  → Hermes drafts reply and optional actions
  → tool mode decides simulate / approve / policy / unrestricted
  → reply action executes idempotently
  → provider delivery is reconciled
  → ticket state and trace update
  → exception or human handoff when needed
```

A ticket has one durable Ecom-OS identity. A Hermes session key is associated with the
ticket to preserve agent context, but current ticket state is always retrieved from
Ecom-OS.

Sticky escalation is an operational state, not a universal restriction. By default, once
a human owns a ticket, new customer messages append and notify without autonomous sends.
An owner may explicitly configure re-entry rules, and that configuration change is
traced.

## 13. Daily brief flow

```text
Ecom-OS closes reporting window
  → computes deterministic metric snapshot
  → gathers activity, exceptions, tasks, and trace links
  → stores immutable brief input
  → Hermes cron or scheduled Ecom-OS run asks Hermes to summarize/prioritize
  → final brief stored
  → Hermes native channel delivers it
  → delivery result and channel message reference recorded
```

If Hermes summarization fails, Ecom-OS sends a deterministic fallback brief. A missing LLM
must not suppress critical alerts or daily metrics.

## 14. Profit and analytics architecture

V1 reports **estimated contribution margin**, not accounting profit.

```text
net sales
+ shipping revenue where applicable
- discounts
- refunds and chargebacks
- product cost / COGS
- payment and marketplace fees
- shipping and fulfilment cost where available
- attributed ad spend
± currency conversion adjustments
= estimated contribution margin
```

Every metric snapshot stores:

- formula version;
- source records and date range;
- source freshness;
- coverage/missing-data flags;
- currency and FX basis;
- attribution assumptions;
- estimated versus confirmed components;
- trace ID for the calculation.

## 15. Extensions and escape hatches

Ecom-OS supports three extension levels:

1. **Configuration and policies:** preferred; no code.
2. **Versioned Ecom-OS plugins:** domain tools, connector adapters, event subscribers,
   pages/widgets, metric sources, and report sections through a public API.
3. **Source edits:** supported owner escape hatch; creates a fork and may require manual
   merges.

Hermes skills, plugins, MCP servers, profiles, and native tools remain separately
installable by the owner. Ecom-OS lists known capabilities and trace coverage but does not
pretend to govern arbitrary external Hermes extensions.

Ecom-OS plugins run as either:

- **declarative/sandboxed extensions** with limited APIs; or
- **trusted native extensions** explicitly marked as instance-privileged.

A trusted native extension is code execution by the owner. Its installation is audited,
and its trace coverage depends on whether it uses Ecom-OS contracts.

## 16. Identity and access

Ecom-OS has its own authenticated users and roles. Hermes native channel authorization
continues to protect access to the agent. `channel_identities` map Hermes platform users
or chats to Ecom-OS identities.

Minimum roles:

- `owner` — all instance and autonomy settings;
- `admin` — users, connections, agents, and policies except ownership transfer;
- `operator` — operational pages and configured approvals;
- `cs_lead` — queue ownership, escalation, and CS approvals;
- `cs_rep` — assigned tickets and granted actions;
- `finance` — financial data and refund approvals;
- `viewer` — selected read-only surfaces;
- service identities — narrow machine scopes.

Tools may use role checks in addition to agent grants. The owner can broaden roles, but
anonymous or ambiguous identity is never treated as authorization.

## 17. Trust boundaries

- Customer and supplier content is untrusted data, not instruction authority.
- Documents and web results carry provenance and trust labels.
- Prompts, skills, policies, and tool grants are configuration and require privileged
  change paths.
- Hermes native terminal/browser tools may act outside Ecom-OS; the UI labels that
  boundary.
- The browser never directly receives connector credentials, Hermes service keys, or
  database credentials.
- Composio or another connector provider owns merchant OAuth tokens when that adapter is
  used; Ecom-OS stores connection references.
- Direct connector adapters must use an encrypted secret store and never expose plaintext
  through logs or tools.
- Every external write identifies the exact store and connection. “Use the latest
  account” behavior is prohibited in Ecom-OS actions.

## 18. Failure and degradation behavior

- Hermes unavailable: structured Ecom-OS pages remain available; chat and agent runs show
  degraded state; deterministic jobs continue where possible.
- Ecom-OS unavailable: Hermes remains usable for non-Ecom work; Ecom-OS tools return a
  clear unavailable result rather than hanging.
- Connector unavailable: actions remain queued or outcome-unknown according to their
  state; last-good read data shows freshness.
- Hook telemetry unavailable: verified Ecom-OS tool/action traces remain intact; Hermes
  observer coverage is marked incomplete.
- Database unavailable: inbound gateways return retryable failures unless a durable edge
  buffer is configured; no in-memory-only acceptance.
- LLM unavailable: retries are bounded; ticket work escalates; deterministic daily brief
  fallback still sends.
- Ambiguous external timeout: action moves to `outcome_unknown` and is reconciled before
  another dangerous attempt.

The engineering slogan is not “never fail.” It is **fail visibly, preserve state, avoid
unintended duplication, and provide a recovery path**.

## 19. What this architecture deliberately does not guarantee

- It cannot make unrestricted autonomy harmless.
- It cannot fully trace an arbitrary shell command, browser interaction, or third-party
  tool that bypasses Ecom-OS contracts.
- It cannot make a self-hosted owner unable to edit or delete their own data.
- It cannot turn estimated contribution margin into audited accounting profit.
- It cannot guarantee Hermes internals remain unchanged; compatibility is maintained
  through pinning, capability negotiation, and conformance tests.
