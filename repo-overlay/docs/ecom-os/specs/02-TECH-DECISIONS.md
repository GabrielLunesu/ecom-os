# 02 — Technical Decisions (ADRs)

> **Status:** accepted unless explicitly marked proposed  
> **Last reviewed:** 2026-06-18

Each record follows **Context → Decision → Rationale → Consequences**. A decision remains
in force until a later ADR explicitly supersedes it.

---

## ADR-001 — One brand per Ecom-OS instance

- **Context:** Ecommerce data, credentials, automations, documents, and agent memory have
  a large blast radius. Retrofitting tenant isolation into an agentic system is risky.
- **Decision:** One Ecom-OS deployment represents one brand. It has one dedicated primary
  Hermes profile and may connect multiple stores belonging to that brand.
- **Rationale:** Operational isolation, simpler backups, clearer ownership, easier
  debugging, and smaller credential blast radius outweigh org-switching convenience.
- **Consequences:** There is no tenant selector in v1. Multi-brand agencies deploy one
  instance per brand. Cross-instance management may be a separate product later.

## ADR-002 — Hermes is an integrated peer system, not an embedded runtime

- **Context:** The original design described an `AgentRuntime` owned by Ecom-OS and a
  brain/hands topology implemented inside it. The intended product is instead a native
  integration with a separately installed Hermes Agent.
- **Decision:** Hermes remains an independent process, profile, state store, and release
  stream. Ecom-OS integrates through documented Hermes protocols and extension points.
  Ecom-OS never forks or patches Hermes core as part of the supported architecture.
- **Rationale:** This preserves native Hermes memory, sessions, channels, cron, skills,
  tools, and future improvements while reducing framework coupling.
- **Consequences:** Ecom-OS must maintain a compatibility matrix, capability negotiation,
  and a thin adapter. Hermes and Ecom-OS upgrades are separate operations.

## ADR-003 — Use different Hermes protocols for interactive and background work

- **Context:** A custom chat UI needs session control, streaming tool events, approvals,
  and branching. Background ticket runs need a durable language-neutral API.
- **Decision:** Use Hermes TUI Gateway JSON-RPC for the interactive Ecom-OS chat and the
  Hermes HTTP API server `/v1/runs` plus event streams for background runs. ACP is not a
  v1 dependency.
- **Rationale:** Each documented interface is used for the task it best supports. This
  avoids writing directly against Hermes internals.
- **Consequences:** `HermesBridge` abstracts both transports. The Ecom-OS backend proxies
  them; the browser never connects to Hermes with a service credential.

## ADR-004 — Ecom-OS tools are exposed through a thin Hermes adapter, with MCP fallback

- **Context:** MCP is the cleanest generic external-tool interface, but exact Hermes
  session/turn correlation is valuable for traceability.
- **Decision:** The preferred integration installs a thin Hermes plugin that registers
  proxy tools and forwards available runtime context to Ecom-OS. A versioned remote HTTP
  MCP server exposes the same tool semantics as a portable fallback.
- **Rationale:** The adapter gives the best native user experience and trace correlation;
  MCP keeps the domain API open and decoupled.
- **Consequences:** Business logic exists only in Ecom-OS. Adapter and MCP schemas are
  generated from the same tool catalog. Trace coverage declares which transport was used.

## ADR-005 — Hermes owns agent memory and session history

- **Context:** Hermes now persists session metadata and full messages in SQLite with FTS
  search, while built-in curated memory remains in `MEMORY.md` and `USER.md` and optional
  memory providers are available.
- **Decision:** Hermes is canonical for its sessions, messages, curated memory, skills,
  profile config, and cron jobs. Ecom-OS stores references and derived metadata, not a
  second canonical transcript.
- **Rationale:** Duplicating Hermes state creates divergence and prevents native resume,
  search, and channel continuity.
- **Consequences:** Ecom-OS never mutates Hermes `state.db`. Full-system backup includes
  the Hermes profile. The UI retrieves sessions through supported Hermes interfaces.

## ADR-006 — Ecom-OS owns operational truth

- **Context:** Native agent memory is not an order database, ticket state machine,
  financial ledger, or source-of-truth policy store.
- **Decision:** Current business data, connector state, tasks, policies, approvals,
  actions, traces, and metrics live in Postgres and are retrieved through Ecom-OS tools.
- **Rationale:** Operational facts require transactions, indexing, concurrency control,
  provenance, freshness, and reconciliation.
- **Consequences:** Prompts and Hermes memory may refer to entities but never become their
  canonical state. Tool handlers re-read current state for state-sensitive writes.

## ADR-007 — No mandatory vector database

- **Context:** The first design alternated between “Hermes memory is enough” and a
  pgvector vault. Neither should become an unnecessary infrastructure requirement.
- **Decision:** V1 uses Hermes native memory/session search plus PostgreSQL metadata and
  full-text document search. Embeddings, pgvector, QMD, or a Hermes memory provider are
  optional additive capabilities.
- **Rationale:** Most operational questions are answered from structured live data. The
  core should remain useful on a small VPS without a separate retrieval stack.
- **Consequences:** The document-search interface is provider-neutral. Optional semantic
  search cannot change source provenance or access-control semantics.

## ADR-008 — Traceability is a hard product invariant

- **Context:** Operators need to diagnose failures across thousands of tickets and
  actions after the fact.
- **Decision:** Every Ecom-OS run, tool invocation, policy decision, approval, action,
  attempt, outcome, and administrative change receives durable correlation identifiers.
  Trace creation cannot be disabled through supported settings.
- **Rationale:** Traceability enables diagnosis, accountability, replay, incident review,
  agent self-inspection, and trustworthy automation.
- **Consequences:** Storage and privacy costs are accepted. Retention is configurable,
  but deletion is itself audited. The product exposes trace search and trace tools to
  Hermes.

## ADR-009 — Distinguish verified, observed, imported, and unknown trace coverage

- **Context:** Ecom-OS can fully instrument its own tools but cannot guarantee complete
  visibility into arbitrary Hermes terminal, browser, plugin, or third-party MCP actions.
- **Decision:** Every trace/span carries a coverage level: `verified`, `observed`,
  `imported`, or `unknown`.
- **Rationale:** Honest partial visibility is more useful than claiming a security or
  audit boundary that does not exist.
- **Consequences:** The UI shows coverage prominently. Incidents may be opened because of
  trace gaps. Supported Ecom-OS actions must always be `verified`.

## ADR-010 — Owner-controlled autonomy, including unrestricted mode

- **Context:** Some operators want strict approvals; others intentionally want agents to
  have broad authority and accept the consequences.
- **Decision:** Each tool grant resolves to `disabled`, `observe`, `approve`, `policy`, or
  `unrestricted`. Unrestricted bypasses Ecom-OS business caps and human approval for that
  granted tool and scope.
- **Rationale:** The owner should control the business risk envelope rather than be
  permanently confined by platform policy.
- **Consequences:** Defaults remain conservative. Enabling unrestricted mode requires an
  explicit owner action and is audited. The UI explains what can happen but does not hide
  undocumented caps behind the setting.

## ADR-011 — Technical integrity remains active in every autonomy mode

- **Context:** “Full permission” should permit intentional risky business actions, not
  accidental duplication, cross-store execution, secret exposure, or untraceable retries.
- **Decision:** Authentication, exact store/account binding, schema validation,
  idempotency, durable action creation, redaction, trace recording, and outcome
  reconciliation are system invariants in all modes.
- **Rationale:** These controls preserve the meaning of the operator's intent; they do not
  substitute platform judgment for that intent.
- **Consequences:** An unrestricted action can still be rejected for malformed input,
  missing identity, invalid connection, duplicate intent, or technical impossibility.
  The rejection reason is explicit and traced.

## ADR-012 — Every external write is an action with attempts

- **Context:** Connector requests can time out after succeeding, be retried, or return
  partial results.
- **Decision:** A write tool first creates an immutable normalized action, then one or more
  attempts. `outcome_unknown` is a first-class state and triggers reconciliation before a
  dangerous retry.
- **Rationale:** Treating an HTTP timeout as a clean failure can duplicate refunds,
  messages, cancellations, or discounts.
- **Consequences:** Connectors must expose provider identifiers, idempotency facilities,
  and reconciliation where available. The action ledger is separate from ordinary logs.

## ADR-013 — Postgres is the durable queue and event store for v1

- **Context:** The initial volume is a few thousand tickets per month, and every extra
  infrastructure service increases operational burden.
- **Decision:** Use a Postgres inbox, outbox, and leased jobs table with row locking for
  v1. Introduce a separate broker only after measured limits are reached.
- **Rationale:** Postgres provides transactions between business state and queued work,
  durable recovery, and a simpler self-hosted deployment.
- **Consequences:** Workers must keep transactions short, use `SKIP LOCKED`, manage leases,
  and expose queue health. High-volume fan-out is not a v1 optimization target.

## ADR-014 — Durable ingestion precedes agent execution

- **Context:** Shopify and inbox providers retry, reorder, and duplicate events. An agent
  run must not be the first durable record of an event.
- **Decision:** Verify and persist inbound events before acknowledging them and before
  invoking Hermes. Agent work consumes normalized durable events.
- **Rationale:** This permits replay, deduplication, incident recovery, and deterministic
  reconstruction.
- **Consequences:** Webhook handlers remain small. Event processing is asynchronous.
  Provider-specific payloads are retained under privacy and retention rules.

## ADR-015 — Connectors are adapters; Composio is the default, not the ontology

- **Context:** Composio can manage OAuth and broad integrations, but the system should not
  couple domain semantics or all future connectors to one provider.
- **Decision:** Define an Ecom-OS connector interface. Ship Composio-backed Shopify and
  inbox adapters first where suitable; permit direct or other-provider adapters later.
- **Rationale:** Stable domain tools should survive connector-provider changes.
- **Consequences:** With Composio, Ecom-OS stores connected-account references and pins the
  exact account for every call. Direct adapters must use an encrypted secret store.

## ADR-016 — Native Hermes channels own operator messaging

- **Context:** Hermes already supports a broad messaging gateway, home channels, scheduled
  delivery, files, threads, and cross-platform messaging.
- **Decision:** Do not create an Ecom-OS Slack/Telegram/Discord bot stack. Daily briefs,
  alerts, and agent conversations use the configured Hermes gateway.
- **Rationale:** This preserves one agent identity and avoids duplicate channel sessions.
- **Consequences:** Ecom-OS maps channel identities for authorization and traces delivery
  references. Hermes remains usable when the Ecom-OS web UI is closed.

## ADR-017 — Daily brief numbers are deterministic; narration may be agentic

- **Context:** The user needs reliable daily revenue, margin, ROAS, ticket, task, and action
  summaries through native channels.
- **Decision:** Ecom-OS freezes the metric and activity snapshot. Hermes may summarize,
  prioritize, and explain it. A deterministic fallback message is always available.
- **Rationale:** Agent prose can be flexible; business numbers must be reproducible.
- **Consequences:** Every brief stores its source window, formula versions, trace links,
  generated text, delivery target, and delivery result.

## ADR-018 — The Ecom-OS main chat is a Hermes client

- **Context:** Building a separate chat loop would fragment memory, sessions, approvals,
  and native channel continuity.
- **Decision:** The main chat directly drives the dedicated Hermes profile through the
  documented programmatic protocol. Ecom-OS adds entity cards, context selection, and
  trace navigation around the native event stream.
- **Rationale:** The user should experience one brain across web and messaging channels.
- **Consequences:** Ecom-OS chat outages do not destroy Hermes history. Chat data remains
  in Hermes; Ecom-OS stores trace links and UI metadata.

## ADR-019 — One primary Hermes profile; additional profiles are explicit

- **Context:** Hermes profiles isolate memory, sessions, skills, cron, credentials, and
  gateway state. Multiple profiles do not automatically share those stores.
- **Decision:** V1 assumes one primary shared brand profile. Additional founder, finance,
  research, or worker profiles are optional and exchange business context through Ecom-OS
  tools rather than assumed shared memory.
- **Rationale:** This keeps the default mental model coherent while preserving an escape
  hatch for privacy or specialization.
- **Consequences:** The UI always displays the active profile. Cross-profile runs carry
  separate Hermes identities and trace links.

## ADR-020 — Access control applies to humans and channels, not only agents

- **Context:** Tool grants alone do not decide which team member may view finance data,
  approve refunds, change autonomy, or access founder-private documents.
- **Decision:** Ecom-OS implements authenticated users, roles, scoped approvals, and
  channel-identity mappings. Hermes gateway allowlists/pairing remain an additional layer.
- **Rationale:** Agent capability and human authority are distinct concerns.
- **Consequences:** A channel message without a mapped Ecom-OS identity receives only the
  configured public/read scope or no Ecom-OS tools. Owner may deliberately broaden roles.

## ADR-021 — Estimated contribution margin, not “profit,” is the v1 financial KPI

- **Context:** True accounting profit depends on data Ecom-OS may not possess and on
  jurisdiction-specific accounting treatment.
- **Decision:** V1 labels the metric `estimated contribution margin` and records formula,
  coverage, attribution, currency, and freshness.
- **Rationale:** The dashboard must not convey false precision.
- **Consequences:** “Profit” may be used conversationally only when the UI and answer state
  the defined calculation. Financial reports are not tax or accounting statements.

## ADR-022 — Source distribution with an immutable supported release path

- **Context:** Operators value source access and may customize deeply, but production
  updates must be reproducible.
- **Decision:** Ship source plus signed/versioned releases and optionally prebuilt images.
  Supported updates deploy an exact commit or image digest, never an ambiguous pull of a
  moving branch.
- **Rationale:** Source openness and reproducible operations are compatible.
- **Consequences:** Core editors own merge conflicts. User-space and versioned extension
  APIs remain the clean-update path. Update tooling snapshots all Ecom-OS and Hermes
  state, not only Postgres.

## ADR-023 — Ecom-OS extensions and Hermes extensions remain separate ecosystems

- **Context:** Ecom-OS needs domain connectors, pages, metrics, and event handlers, while
  Hermes already has skills, plugins, tools, profiles, and MCP servers.
- **Decision:** Ecom-OS publishes its own extension API and does not wrap all Hermes
  extensions as Ecom-OS plugins. The integrations may reference each other but retain
  separate ownership and versioning.
- **Rationale:** Blurring the ecosystems would make compatibility, trust, and trace
  coverage impossible to explain.
- **Consequences:** The settings UI shows both known Ecom-OS extensions and detected
  Hermes capabilities, with clear provenance and trust labels.

## ADR-024 — Trusted code is treated as owner-level code execution

- **Context:** A Python or JavaScript plugin can usually access far more than its declared
  manifest if it runs in the application process.
- **Decision:** Label extensions as `declarative/sandboxed` or `trusted native`. Trusted
  native installation is an owner action equivalent to installing software on the VPS.
- **Rationale:** Manifests alone are not a sandbox.
- **Consequences:** Safety guarantees apply only to supported contracts. Trusted code is
  audited, versioned, and shown in system health; it may reduce trace completeness.

## ADR-025 — Capability negotiation instead of optimistic assumptions

- **Context:** Hermes evolves quickly, and optional extras determine available protocols,
  tools, hooks, and channels.
- **Decision:** On startup, Ecom-OS records Hermes version, adapter version, API
  capabilities, configured profile, and required feature checks. Features fail closed or
  degrade individually according to their dependency.
- **Rationale:** A declared version is not sufficient proof that a runtime surface is
  enabled and healthy.
- **Consequences:** Production readiness includes a Hermes conformance suite. Unsupported
  combinations show actionable health errors rather than causing silent data loss.
