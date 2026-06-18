# Documentation Changelog — Original Draft to v2.0

> **Date:** 2026-06-18  
> **Scope:** complete architecture rewrite before production implementation

This document records the material changes from the original six-document design to the
v2 production baseline. It exists so later contributors do not accidentally reintroduce
superseded assumptions.

## 1. Why the rewrite was necessary

The original documents established a strong product thesis—one brand per instance,
source availability, capability-aware agents, sticky escalation, profit-first operation,
and a clean core/user-space boundary. They also left several production-critical areas
underspecified and described Ecom-OS as if it owned a swappable Hermes runtime.

The clarified product is different:

- Hermes remains the agent product and is integrated natively.
- Ecom-OS is the ecommerce data, workflow, dashboard, action, and trace system beside it.
- The owner may deliberately grant broad or unrestricted authority.
- Traceability, diagnosis, idempotency, and reconciliation are the durable platform value.
- The main Ecom-OS chat is a Hermes conversation, not a separate copilot.
- Daily operational summaries are delivered through native Hermes channels.

The v2 set makes those choices normative and adds the previously missing Runtime and
Build specifications.

## 2. Preserved principles

The following original principles remain:

- one brand per instance;
- one dedicated primary Hermes profile for the brand;
- self-hosted/source-available operation;
- opinionated defaults with user-space customization;
- exact tool capability matters more than prompt wording;
- frontend is not an authorization boundary;
- customer content is untrusted;
- sticky escalation;
- idempotent processing;
- graceful degradation;
- tested migrations and clean update paths;
- estimated economic outcome matters more than vanity revenue;
- extensions should not require routine core edits.

They have been made more precise where necessary.

## 3. Major architectural changes

### 3.1 `AgentRuntime` ownership replaced by peer integration

**Original:** Ecom-OS routed all execution through one owned `AgentRuntime` abstraction,
with Hermes as the v1 implementation and an in-app deterministic fallback.

**V2:** Hermes is an independent peer with its own process, profile, release lifecycle,
SQLite session state, memory, tools, cron, and channels. Ecom-OS uses an owned
`HermesBridge` only to normalize official protocols; it is not a replacement runtime.

**Reason:** The product is an integration with Hermes, not an extension or embedded agent
framework.

### 3.2 Brain/hands topology replaced by per-tool grants and action contracts

**Original:** A self-improving brain profile delegated money-touching work to leaf “hands”
subagents with closed toolsets.

**V2:** Hermes may use its native profile and delegation model. Ecom-OS resolves a
versioned grant for each tool invocation and routes supported external writes through a
durable action executor. The owner may use conservative or unrestricted grants.

**Reason:** Subagent topology is a useful configuration pattern, not the universal product
security/operating model. Traceable execution and exact grants survive changes in Hermes
agent structure.

### 3.3 Mandatory business guardrails replaced by owner sovereignty

**Original:** Customer service was permanently denied refund capability and money-touching
agents were described as deterministic by construction.

**V2:** Safe defaults remain, and refund execution is deferred from the first v1 pilot,
but the owner may explicitly grant broad or unrestricted capabilities when a tool exists.
Ecom-OS does not impose hidden business caps in unrestricted mode.

Technical-integrity invariants remain mandatory: authentication, exact account binding,
schema validation, idempotency, durable actions, redaction, trace recording, and
reconciliation.

**Reason:** The operator owns the store and risk envelope. Reliability controls preserve
intent; they do not substitute the platform's business judgment for the owner's.

### 3.4 “Deterministic hands” replaced by an honest action model

**Original:** Closed toolsets were equated with deterministic money-touching behavior.

**V2:** The model may still choose an action and arguments. Ecom-OS records the exact
proposal, state, grant, policy, approval, action digest, connector attempts, and outcome.
It prevents duplicate/ambiguous retries but does not claim the model's business judgment
was deterministic or correct.

**Reason:** Tool restriction limits capability; it does not prove correct target,
calculation, policy interpretation, or outcome.

### 3.5 Traceability elevated to a product invariant

**Original:** An `audit` table and activity concepts existed but no complete execution
model was specified.

**V2:** The data model now defines events, jobs, traces, runs, spans, tool invocations,
actions, attempts, evidence, approvals, audits, incidents, daily briefs, coverage levels,
retention, replay, and reconciliation.

Every supported Ecom-OS action is searchable from trigger to provider outcome. Hermes
receives read-only trace/incident tools for retrospective diagnosis.

### 3.6 Trace coverage is explicitly bounded

**Original:** The permission chokepoint and plugin model implied complete control of agent
capabilities.

**V2:** Coverage is labeled `verified`, `observed`, `imported`, or `unknown`. Arbitrary
Hermes terminal, browser, native plugin, or third-party MCP actions may bypass Ecom-OS.
The system exposes that boundary rather than claiming a universal audit perimeter.

### 3.7 Main chat is now Hermes-native

**Original:** A chat copilot existed as a separate trust surface, behind an Ecom-owned
runtime interface.

**V2:** The main dashboard chat creates/resumes native Hermes sessions through the TUI
Gateway JSON-RPC contract, streams native events, supports interruption/branching and
links Ecom-OS tool/action traces. Ecom-OS stores references, not a second canonical
transcript.

### 3.8 Background runs use supported Hermes APIs

**Original:** Background runtime semantics were referenced in a missing spec.

**V2:** Durable Ecom-OS jobs initiate Hermes asynchronous runs through the documented HTTP
API, consume lifecycle events, recover status after transport loss, and reconcile adapter
telemetry.

### 3.9 Native channel and daily-brief architecture added

**Original:** Hermes cron/insights were mentioned, but no operator communication contract
was defined.

**V2:** Hermes owns Telegram, Slack, Discord, email, and other supported native channels.
Ecom-OS creates a deterministic daily snapshot, optionally asks Hermes to narrate it, and
records a traced, idempotent delivery intent. The brief covers economics, CS, actions,
tasks, research, incidents, health, and links.

### 3.10 Hermes memory model corrected and clarified

**Original:** Hermes persistent memory was treated as the complete brand vault and as the
reason no external vector database was required. Another document simultaneously defined
a Markdown/pgvector vault.

**V2:** Hermes remains canonical for its own curated memory, user memory, session history,
skills, and profile state. Ecom-OS keeps current operational truth in Postgres and source
documents in a user-space vault. Postgres full-text search is the v1 document baseline;
optional Hermes memory providers, embeddings, or pgvector may be added without changing
provenance or access control.

**Reason:** Native memory and SQLite session search are valuable but serve different roles
from live order/ticket/metric state and large versioned document corpora.

### 3.11 Connector ontology generalized

**Original:** Every connector was required to go through Composio.

**V2:** Composio remains a preferred/default adapter for many integrations, but connector
semantics are owned by Ecom-OS. Direct adapters and other providers may implement the same
identity, idempotency, rate-limit, trace, attempt, and reconciliation contract.

**Reason:** The architecture should not make one vendor the domain model. Exact connection
references and provider-managed OAuth remain supported.

### 3.12 Plugin model split from Hermes extensions

**Original:** One broad Ecom-OS plugin contract included tools, connectors, UI, hooks,
agent templates, and other runtime behavior.

**V2:** Ecom-OS extensions and Hermes skills/plugins/MCP/profiles remain separate
versioned ecosystems. Ecom-OS extensions are classified as declarative/sandboxed or
trusted native. Trusted native code is explicitly owner-level code execution.

**Reason:** A manifest is not a sandbox, and the product cannot guarantee one permission
chokepoint for arbitrary in-process code.

### 3.13 Human and channel authorization added

**Original:** Agent tool permissions were detailed; authenticated team roles and channel
identity were not.

**V2:** Users, roles, service identities, channel identities, approval scopes, private
knowledge labels, and recent-auth requirements are specified. Hermes gateway permissions
and Ecom-OS roles are separate layers.

### 3.14 Update model made reproducible

**Original:** Update meant back up Postgres, `git pull <release-tag>`, rebuild, migrate,
health-check, and roll back.

**V2:** Supported releases identify an exact commit/image digest, lockfiles, schema range,
Hermes compatibility, adapter/schema version, and extension API. Updates snapshot all
state, preserve inbound events, use expand-compatible migrations, stage health checks,
and state honestly when restore—not code rollback—is required.

### 3.15 Backup model expanded to full instance

**Original:** Postgres backup was emphasized despite user-space also containing Hermes
state, vault files, plugins, and configuration.

**V2:** A valid recovery set includes Postgres, complete Hermes profile, vault/artifacts,
extensions, deployment metadata, checksums, and secret-restoration instructions. Pending
external actions are reconciled before writes resume.

### 3.16 Financial terminology corrected

**Original:** The dashboard led with “profit” defined as revenue minus COGS, ad spend, and
fees.

**V2:** V1 uses **estimated contribution margin** and exposes formula, currency, coverage,
attribution, missing inputs, and freshness. It is not an accounting or tax statement.

### 3.17 Generic Sheets moved out of v1

**Original:** Manual Sheets and formula columns were an explicit early architectural
seam.

**V2:** A generic spreadsheet/formula product is removed from the v1 release gate. Domain
pages, tasks, metric evidence, exports, and extensions are prioritized.

**Reason:** Sheets added substantial UI/formula/data-source scope without proving the
Hermes integration, WISMO, trace, or recovery thesis.

## 4. Newly specified production systems

The v2 set adds complete contracts for:

- durable webhook/event inbox;
- Postgres-leased jobs and ordering;
- transactional outbox;
- Hermes compatibility/capability probe;
- dashboard JSON-RPC bridge;
- asynchronous background runs;
- adapter and MCP tool schema generation;
- invocation/action/result envelopes;
- effective grants and unrestricted mode;
- exact approval digest;
- action attempts and ambiguous outcomes;
- trace coverage and evidence;
- incident diagnosis;
- channel identity mapping;
- deterministic daily briefs;
- full-instance backup/restore;
- emergency pause and degraded modes;
- page-by-page product requirements;
- vertical build slices and release gates.

## 5. File mapping

| Original file | V2 treatment |
|---|---|
| `README.md` | Replaced with a complete index, glossary, ownership model, and compatibility baseline. |
| `00-VISION.md` | Rewritten around Hermes-native integration, owner sovereignty, and traceability. |
| `01-ARCHITECTURE.md` | Replaced embedded-runtime model with peer topology, durable events/actions, and native channels. |
| `02-TECH-DECISIONS.md` | Replaced with 25 accepted ADRs covering the clarified system. |
| `03-ENGINEERING.md` | Expanded into concrete boundaries, queue/action semantics, conformance, testing, observability, and release discipline. |
| `AGENTS.md` | Replaced old mandatory business constraints with integration, trace, action, owner-autonomy, and integrity invariants. |
| Missing Runtime Spec | Added `ECOM-OS-RUNTIME-SPEC.md`. |
| Missing Build Spec | Added `ECOM-OS-BUILD-SPEC.md`. |
| No complete trace/data spec | Added `04-DATA-AND-TRACEABILITY.md`. |
| No complete operations spec | Added `05-OPERATIONS-AND-SECURITY.md`. |

## 6. Migration implications for any prototype code

Before preserving code written against the original design, inspect for these obsolete
patterns:

- an `AgentRuntime` abstraction that owns or replaces Hermes;
- direct import of Hermes Python internals into domain code;
- direct reads/writes of Hermes SQLite;
- a second canonical chat transcript;
- separate brain/hands profiles treated as a hard platform invariant;
- fixed denial of owner-requested capabilities in domain code;
- connector writes without actions/attempts/reconciliation;
- “success” inferred from request completion or model text;
- Composio account selection without exact connected-account binding;
- an audit table without trace/action correlation;
- Postgres-only backup called full backup;
- `git pull` of an ambiguous tag/branch as production release deployment;
- “profit” KPI without coverage and formula;
- broad native plugins described as sandboxed by manifest;
- custom Slack/Telegram delivery that duplicates Hermes gateway;
- chat UI that bypasses native Hermes sessions.

Such code is not automatically discarded, but it must be reshaped behind the v2
contracts before production use.

## 7. Decision summary

The revised architecture does not make Ecom-OS smaller in ambition. It makes the product
boundary clearer:

- **Hermes thinks, remembers, converses, schedules, delegates, and speaks through native
  channels.**
- **Ecom-OS knows the current business, organizes work, executes ecommerce actions, shows
  the operator what matters, and preserves the evidence of what happened.**
- **The owner decides how much authority to grant.**
- **The system makes consequences inspectable and recoverable instead of pretending risk
  can be removed by prompt wording.**
