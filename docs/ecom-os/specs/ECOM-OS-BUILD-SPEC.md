# Ecom-OS Build Specification

> **Status:** normative v1 product and delivery specification  
> **Spec version:** 1.0.0  
> **Last reviewed:** 2026-06-18

This specification turns the architecture into a buildable sequence. It defines the v1
surfaces, information architecture, vertical slices, acceptance tests, and release gates.
It does not authorize shortcuts around the runtime, trace, security, or data contracts.

## 1. V1 product boundary

V1 proves that one ecommerce operator can use one dedicated Hermes profile and Ecom-OS as
one coherent operating environment.

Included:

- one brand;
- one primary Hermes profile;
- one Shopify store;
- one Gmail or Outlook customer-service inbox through one supported connector path;
- authenticated small-team access;
- the Hermes-backed Ecom-OS main chat;
- current order, customer, ticket, task, metric, trace, and document tools;
- durable inbound event ingestion and synchronization;
- WISMO classification, drafting, human review, policy automation, unrestricted mode,
  sticky escalation, and outbound reply execution;
- owner-configurable tool grants and approvals;
- trace explorer, action ledger, and incident review;
- daily brief through one configured native Hermes channel;
- estimated contribution margin with evidence, freshness, and coverage;
- full-instance backup, restore, and supported updates;
- a minimal versioned Ecom-OS extension contract after the core path is stable.

Excluded from the v1 release gate:

- multi-brand tenancy inside one instance;
- arbitrary workflow-builder UI;
- plugin marketplace or execution of unreviewed remote code;
- full accounting, tax, or inventory-planning suite;
- automated ad campaign writes;
- autonomous merchandising/product changes;
- refund execution as part of the first pilot;
- generic spreadsheet/formula product;
- broad mobile/PWA parity;
- a promise to trace arbitrary non-Ecom Hermes terminal/browser activity completely.

Refund proposals and imported refund history MAY be visible. Actual refund execution is a
post-v1 capability unless separately accepted through the same action and reconciliation
gates.

## 2. Navigation and page map

### 2.1 Primary navigation

```text
Today
Chat
Customer Service
Orders
Customers
Finance
Tasks
Activity
Knowledge
Agents
Settings
System
```

The navigation is role-aware, but the backend independently enforces access.

### 2.2 Global interaction patterns

Every page supports the following where relevant:

- global brand/store/timezone context;
- command palette;
- search;
- “Ask Hermes about this” with entity context;
- trace/evidence links;
- freshness and coverage indicators;
- permission-aware actions;
- stable shareable URLs;
- loading, empty, stale, partial, unavailable, and error states;
- keyboard navigation for core workflows.

External actions never disappear into a toast. The originating page shows the action
state and links to its trace.

## 3. Page specifications

### 3.1 Today — `/`

Purpose: answer “what needs my attention now?” rather than present a decorative analytics
wall.

Required modules:

- daily brief status and latest brief;
- operational attention queue;
- pending approvals;
- tickets needing representatives;
- oldest and growing ticket backlog;
- failed and outcome-unknown actions;
- connector, Hermes, queue, backup, and data-freshness warnings;
- tasks due/overdue;
- yesterday's estimated contribution margin/revenue/ad-spend context;
- significant changes/anomalies with trace/evidence links;
- recent completed research/insights;
- recent autonomy/grant changes.

Each card states:

- what happened;
- why it is shown;
- time window and timezone;
- source/freshness/coverage;
- primary action;
- trace or source link.

Acceptance:

- no card presents stale data as current;
- every numeric card links to calculation evidence;
- a system without historical data renders useful onboarding/empty states;
- role restrictions are applied before data reaches the client.

### 3.2 Main Chat — `/chat`

Purpose: provide a native Hermes conversation surface inside the ecommerce context.

Required layout:

- session list/search and new-session action;
- central streamed conversation;
- visible tool progress/results;
- attachment/entity context chips;
- model/session status where available;
- cancel/interrupt;
- clarification and approval panels;
- expandable trace drawer;
- context panel for linked ticket/order/customer/task/document;
- resume/branch actions;
- error and reconnect state.

Required behavior:

- sessions are created/resumed in Hermes, not a second chat database;
- the URL identifies the Hermes session reference through an Ecom-OS-safe ID;
- Ecom-OS tool results render as structured entity/action/evidence cards;
- each user turn creates a trace and links child tools/actions;
- users may ask Hermes to inspect traces or incidents through read-only tools;
- browser users receive only approved protocol operations;
- reconnect queries session status/history rather than inventing completion.

Example acceptance prompt:

> “Open ticket 8142, get the order, explain why the response was sent, and compare the
> active policy with the one used at the time.”

The answer must use current/historical Ecom-OS tools, show evidence, and link the trace.

### 3.3 Customer Service queue — `/customer-service`

Purpose: manage tickets and see automation quality at queue scale.

Required views/filters:

- all/open/waiting/customer-replied/needs-rep/resolved;
- assignment and owner;
- automation state;
- classification/category;
- age/SLA;
- store/inbox;
- risk/confidence when available;
- failed/unknown action;
- date range and full-text search.

Required columns/cards:

- customer and subject;
- latest message preview;
- order/shipping status when linked;
- state and assignment;
- agent/human activity;
- last action and trace;
- last updated.

Bulk actions are limited to safe state/assignment changes in v1. Bulk external sends are
not a v1 feature.

### 3.4 Ticket detail — `/customer-service/tickets/[ticketId]`

Required panels:

- threaded conversation with source/channel markers;
- customer and order context;
- current state, assignment, tags, and escalation history;
- agent draft/current proposed action;
- final sent replies and provider message IDs;
- evidence used;
- run/tool/action timeline;
- approvals;
- internal notes/tasks;
- “Ask Hermes about this ticket”;
- sticky escalation controls;
- reopen/resolve/assign actions.

A ticket reply composer clearly distinguishes:

- draft only;
- send as human;
- approve agent action;
- edit, which creates a new action digest;
- send state (`queued`, `executing`, `succeeded`, `outcome_unknown`, etc.).

A reply is never shown as sent solely because the browser submitted it.

### 3.5 Orders — `/orders` and `/orders/[orderId]`

V1 is read-oriented except actions explicitly added through the action contract.

Required list/detail data:

- order identity, dates, customer, value/currency;
- payment/fulfilment/shipping/refund/cancellation state;
- line items and quantities;
- tracking and carrier events;
- discounts, taxes, shipping, and fees where available;
- COGS coverage and estimated contribution;
- linked tickets/actions/traces;
- source and last synchronization;
- raw upstream reference accessible only to authorized users.

The detail page can open a contextual Hermes chat and must identify missing or stale
components.

### 3.6 Customers — `/customers` and `/customers/[customerId]`

Required data:

- identity and contact fields subject to role;
- orders and lifetime context;
- tickets and current escalations;
- discount/refund/action history;
- notes/tasks;
- source/freshness;
- trace links.

Do not display a generated customer “score” without formula, source, and intended use.

### 3.7 Finance — `/finance`

Purpose: expose operational economics, not pretend to be an accounting package.

Required KPI set:

- revenue context;
- refunds/returns context;
- discounts;
- payment/platform fees where available;
- COGS coverage;
- ad spend and attribution window;
- shipping/fulfilment costs where available;
- estimated contribution margin;
- missing-cost and stale-source counts;
- currency/FX basis.

Required interactions:

- date/store/currency filters;
- daily/weekly trend;
- drill-down to orders and calculation components;
- source coverage panel;
- formula/version display;
- reconciliation warnings;
- “Ask Hermes why this changed” with metric snapshot context.

No number may be labeled audited profit. Missing components reduce coverage and are
visible in both UI and tool results.

### 3.8 Tasks — `/tasks`

Required v1 behavior:

- Kanban and list views;
- assignee, due date, priority, status, entity links;
- human- or agent-created provenance;
- comments/activity;
- trace link for agent-created tasks;
- personal and team filters;
- daily-brief inclusion.

Task creation is a database write, not an external action. It is still traced and audited
when agent-created.

### 3.9 Activity — `/activity`

Purpose: searchable operational history.

Required tabs/filters:

- traces;
- actions;
- tool invocations;
- administrative audit;
- incidents;
- trace gaps;
- date/timezone;
- actor/user/agent/profile/session;
- ticket/order/customer/task;
- tool/action type;
- status/error;
- autonomy mode/policy/approval;
- coverage.

The default view groups low-level spans into understandable runs. Raw safe details remain
available on demand.

### 3.10 Trace detail — `/activity/traces/[traceId]`

Required sections:

- summary and current outcome;
- coverage statement;
- linked entities/session/run/job/event;
- ordered timeline of spans;
- visible prompt/task and available config/skill/policy hashes;
- tool inputs/results with redaction;
- evidence and freshness;
- approvals;
- actions and attempts;
- provider outcome/reconciliation;
- errors and retry history;
- related traces/incidents;
- operator and agent analysis notes;
- export subject to permissions.

The page must help answer:

- What triggered this?
- Who or what acted?
- What information was available?
- What instructions/configuration applied?
- What decision was proposed?
- What grant/policy/approval allowed it?
- What exact action was attempted?
- What did the provider actually do?
- What is uncertain or missing?

### 3.11 Incident detail — `/activity/incidents/[incidentId]`

Required fields:

- severity/status/owner;
- detection source and timeline;
- affected customers/orders/tickets/actions/time range;
- containment steps;
- evidence and trace links;
- root-cause category and confidence;
- impact estimate;
- compensation/correction state;
- follow-up tasks/tests/docs;
- agent analysis notes separated from verified findings.

### 3.12 Knowledge — `/knowledge`

V1 manages source documents and retrieval, not a generic vector database interface.

Required behavior:

- upload/register text, Markdown, PDF, URL snapshot, or note subject to supported
  extractors;
- version, source, effective date, owner, access label, trust label;
- full-text search and preview;
- replacement/supersession history;
- ingestion/index status;
- link a document to policy/SOP/entity;
- test retrieval as a selected role;
- open contextual Hermes chat.

Hermes native memory is shown separately as a native capability/status link. Ecom-OS does
not present its document vault as the entirety of Hermes memory.

### 3.13 Agents — `/agents`

Purpose: explain and configure the Ecom-OS-facing runtime without rebuilding Hermes
administration.

Required sections:

- primary Hermes profile and compatibility status;
- active adapter/MCP transport and schema hash;
- detected capabilities and native channel/cron health summaries;
- Ecom-OS tool catalog;
- grants by tool/profile/store/channel/role;
- autonomy mode and expiry;
- recent runs/actions/trace gaps;
- prompts/templates owned by Ecom-OS workflows;
- links/instructions to native Hermes profile administration.

The page must distinguish:

- Ecom-OS tools and grants;
- native Hermes tools/configuration;
- third-party Hermes extensions;
- trace coverage for each.

### 3.14 Approvals — `/approvals`

Required queues:

- pending Ecom-OS action approvals;
- approved/rejected/expired history;
- exact action preview/digest;
- requester, run, tool, store, target, amount/body;
- evidence and current-state validation;
- approver scope;
- linked trace.

Changing an approved action creates a new action/proposal. Approval is not a reusable
blank cheque.

### 3.15 Settings — `/settings/*`

Subpages:

- `/settings/general` — brand, locale, currency, timezone, retention profile;
- `/settings/team` — users, roles, invitations, recovery;
- `/settings/connections` — stores, inbox, ads, payment, supplier, connector health;
- `/settings/channels` — channel identity mappings and daily-brief destination;
- `/settings/autonomy` — grants/modes/policies/emergency pause;
- `/settings/notifications` — alerts and briefing schedule/preferences;
- `/settings/extensions` — Ecom-OS extensions and trust class;
- `/settings/data` — sync, export, deletion, retention;
- `/settings/developer` — API/service identities, webhooks, MCP endpoint, schema versions.

High-risk changes require recent authentication and create audit records.

### 3.16 System — `/system`

Required status:

- Ecom-OS version/commit/image digest;
- database/schema/migration state;
- Hermes version/profile/adapter and conformance result;
- queue/inbox/outbox health;
- action/reconciliation backlog;
- connector health;
- trace gaps;
- disk/storage;
- backup/restore status;
- extensions and compatibility;
- recent updates/incidents;
- maintenance mode and emergency pause.

Required operations subject to owner permissions:

- run health/conformance checks;
- create/verify backup;
- view restore instructions;
- enter/leave maintenance mode;
- pause/resume writes/jobs;
- rotate a service identity;
- start a supported exact-version update.

## 4. Cross-cutting data contracts

Every frontend query/mutation uses typed backend contracts. At minimum, every returned
operational object supports:

```text
id
brand_id/store_id as applicable
source/source_id
created_at/updated_at/source_updated_at
freshness_status
coverage_status
permissions
primary_trace_id where applicable
```

Money values use integer minor units plus ISO currency. Timestamps are UTC in storage and
render in the user's selected timezone with the effective timezone visible in reports.

External writes return action state, not only `200 OK`.

## 5. Build sequence

Each slice is independently demonstrable and shippable to a non-production environment.
A later slice may not hide a failing earlier gate.

### Slice 0 — Contract and risk spikes

Deliver:

- accepted v2 documentation set;
- repository skeleton and dependency locks;
- Hermes version pin and compatibility matrix;
- TUI Gateway/API server protocol spike;
- adapter and MCP read-tool spike;
- trace correlation spike;
- native channel/cron delivery spike;
- connector timeout/idempotency spike;
- full Hermes profile + Postgres backup/restore spike.

Acceptance:

- all required Hermes conformance behaviors are demonstrated against the pinned release;
- no direct Hermes SQLite writes are used;
- one Ecom-OS read tool appears in a native Hermes run and links to a trace;
- one test message is delivered through a native Hermes channel;
- one simulated ambiguous connector outcome is reconciled;
- a full restore brings back the Hermes session and Ecom-OS trace linkage.

**Gate:** Do not begin customer-facing automation until this slice passes.

### Slice 1 — Production skeleton and identity

Deliver:

- deployable web/API/worker/Postgres topology;
- owner bootstrap and authentication;
- roles/service identities;
- structured logging, error model, health endpoints;
- migration runner;
- base design system/navigation;
- audit records for identity/config changes;
- CI and test harness.

Acceptance:

- bootstrap closes after owner creation;
- unauthorized page/API/socket access fails server-side;
- no secret appears in logs or client responses;
- database restart and worker lease recovery succeed;
- baseline backup and migration tests run in CI.

### Slice 2 — Durable core and trace ledger

Deliver:

- IDs/common event envelope;
- event inbox/outbox and jobs;
- traces/runs/spans/tool invocations;
- actions/attempts/state history;
- evidence, audit, incidents;
- Activity list and trace-detail shell;
- trace search API and Hermes trace read tools.

Acceptance:

- duplicate events are accepted once;
- expired job leases recover;
- a seeded run/action is searchable by all primary entity keys;
- timeline ordering and coverage labels are correct;
- restricted evidence is not returned to an unauthorized role.

### Slice 3 — Hermes bridge and main chat

Deliver:

- capability probe/conformance UI;
- backend-managed TUI Gateway connection;
- session list/create/resume/history;
- streamed messages/tool events;
- interrupt and reconnect;
- trace per turn;
- adapter/MCP catalog integration;
- structured rendering for Ecom-OS tool results.

Acceptance:

- an existing Hermes session resumes with canonical history;
- a prompt streams without browser access to Hermes service credentials;
- disconnect/reconnect recovers status;
- a read tool creates a verified invocation under the chat trace;
- a native non-Ecom tool is not mislabeled verified;
- main chat remains a Hermes session, not a copied transcript.

### Slice 4 — Connections and operational read model

Deliver:

- store/inbox connection setup;
- exact connection binding;
- signed webhook ingress;
- initial and incremental Shopify/inbox sync;
- normalized stores/orders/customers/products/tickets/messages;
- freshness and source coverage;
- Orders/Customers basic pages;
- read tools for stores/orders/customers.

Acceptance:

- a real/sandbox order is retrieved by ID and customer;
- a duplicate webhook changes state once;
- wrong-account fixtures are rejected;
- connector outage shows last-good freshness;
- the agent can answer current order status with evidence.

### Slice 5 — Customer-service queue and shadow agent

Deliver:

- ticket threading/state history;
- queue/detail UI;
- WISMO classification workflow;
- Hermes background run integration;
- draft/proposal storage;
- assignment and sticky escalation;
- shadow-mode quality reporting;
- ticket/order/customer/trace tools.

Acceptance:

- duplicate/out-of-order messages thread correctly;
- one inbound trigger creates one active workflow;
- customer content remains evidence and cannot change grants/config;
- `needs_rep` replies append/notify without unintended autonomous restart;
- every draft links to run, prompt/template hash, evidence, and trace;
- no outbound message is possible in observe mode.

### Slice 6 — Reply action executor and approvals

Deliver:

- send-reply tool/action schema;
- exact action digest and intent key;
- approval queue/detail;
- connector attempt recording;
- timeout classification/reconciliation;
- human send and agent-approved send;
- action state UI in ticket and trace pages.

Acceptance:

- replay sends one message;
- concurrent send requests produce one action/provider message;
- editing body invalidates approval;
- expired/stale approval fails safely;
- timeout-after-provider-acceptance resolves without duplicate;
- every provider message has action/attempt/trace linkage.

### Slice 7 — Policy and unrestricted autonomy

Deliver:

- grant model and resolution engine;
- `disabled`, `observe`, `approve`, `policy`, `unrestricted` modes;
- owner settings and impact preview;
- versioned reply policies;
- emergency pause;
- audit and daily/Activity reporting by mode.

Acceptance:

- mode matrix passes the runtime conformance fixtures;
- unrestricted execution bypasses Ecom-OS business approval/caps;
- malformed, wrong-store, duplicate, and disconnected-account requests still reject;
- grant changes are searchable and linked to subsequent actions;
- emergency pause blocks new writes without losing queued actions.

### Slice 8 — Trace explorer and incident diagnosis

Deliver:

- complete Activity filters;
- trace timeline/detail;
- prompt/config/policy comparison;
- coverage-gap view;
- incident create/contain/analyze/close workflow;
- Hermes trace/incident tools;
- export with role-aware redaction.

Acceptance:

- an operator can locate an arbitrary seeded bad ticket from a date range;
- the page identifies trigger, instructions, evidence, grant, action, and outcome;
- Hermes can inspect the same trace and add an analysis note;
- agent analysis is visibly distinct from verified findings;
- partial observer coverage is not represented as complete.

### Slice 9 — Tasks and Today

Deliver:

- tasks/assignees/entity links;
- Today attention model;
- pending approvals, incidents, backlog, failed actions, health, and due tasks;
- agent task-creation tool;
- deterministic attention ranking explanation.

Acceptance:

- every attention item links to source/trace;
- role-restricted cards do not leak counts or content;
- agent-created tasks include provenance;
- empty, stale, and degraded states are useful.

### Slice 10 — Finance and metric evidence

Deliver:

- normalized order economics/ad-spend/cost inputs available from selected connectors;
- estimated contribution margin engine;
- metric snapshots/components/evidence;
- Finance page;
- metric tools and “explain change” chat context;
- missing-data/FX/attribution/freshness display.

Acceptance:

- calculations use integer minor units and tested formulas;
- every KPI drills to components;
- missing COGS/ad/fee inputs visibly reduce coverage;
- a metric cannot be labeled accounting profit;
- Hermes narration cites metric snapshots rather than inventing numbers.

### Slice 11 — Native daily brief

Deliver:

- deterministic daily snapshot;
- optional Hermes narration workflow;
- deterministic fallback renderer;
- native channel identity/destination setup;
- Hermes cron scheduling or owner-approved native schedule setup;
- delivery intent, idempotency, status, and trace;
- Today brief panel.

Acceptance:

- date window/timezone are correct;
- all numbers reconcile to metric/ticket/action/task sources;
- narration failure still produces a usable brief;
- a configured native channel receives the brief;
- rerun does not duplicate delivery;
- delivery failure is visible and retryable.

### Slice 12 — Knowledge and contextual retrieval

Deliver:

- document vault/version/access/trust model;
- extraction and Postgres full-text index;
- Knowledge page;
- role-filtered document search/get tools;
- source links and supersession;
- contextual “Ask Hermes” flows.

Acceptance:

- an unauthorized role cannot retrieve restricted document content;
- a superseded SOP is identifiable in a historical trace;
- current search results carry source/version/effective date;
- no mandatory embedding service is required.

### Slice 13 — Operations, update, and extension baseline

Deliver:

- System page and health dimensions;
- full-instance backup/verify/restore workflow;
- maintenance mode;
- exact-release update controller;
- extension manifests/trust labels/version checks;
- production runbooks and installation guide.

Acceptance:

- upgrade N-1 to N with realistic data succeeds;
- deliberate failed candidate health check leaves a recoverable system;
- restore includes Hermes sessions/memory/config, Ecom-OS traces/actions, and vault;
- pending actions reconcile before writes resume;
- incompatible extensions are blocked or disabled visibly;
- exact release identity is shown.

## 6. WISMO workflow acceptance specification

The first live workflow is done only when all scenarios pass against a sandbox or tightly
controlled pilot account.

### 6.1 Normal delivery-status reply

Given a new WISMO message and a linked fulfilled order with current tracking:

- event is durably accepted;
- one ticket trigger starts;
- Hermes retrieves current ticket/order/tracking;
- draft includes no fabricated status/date;
- evidence links identify the provider records;
- selected autonomy mode is applied;
- at most one reply is delivered;
- provider message ID is recorded;
- ticket transitions correctly;
- trace is searchable.

### 6.2 Missing order

When no reliable order match exists:

- the agent does not guess;
- it asks for permitted identifying information or escalates;
- no write beyond the configured reply behavior occurs;
- evidence/ambiguity is visible.

### 6.3 Multiple possible orders/customers

- ambiguous identity is not resolved by recency alone;
- no sensitive order details are exposed before identity rules pass;
- the workflow asks for clarification or routes to a representative.

### 6.4 Prompt injection in ticket text

A message instructing the agent to reveal secrets, change policy, ignore tools, issue a
refund, or contact another customer:

- remains untrusted evidence;
- cannot alter grant/autonomy/configuration;
- cannot expose credentials;
- cannot choose another store/account;
- any proposed reply/action remains governed by the normal contract;
- the trace retains a safe representation for review.

### 6.5 Duplicate and race

Two identical webhooks and two workers racing the same ticket:

- create one normalized trigger;
- produce at most one active run per configured ordering rule;
- produce one reply action intent;
- send at most one provider message.

### 6.6 Provider timeout

When the provider accepts a message but the connector times out:

- attempt persists;
- action becomes `outcome_unknown`;
- automatic dangerous retry waits;
- reconciliation finds or fails to find the provider message;
- final state and confidence are visible;
- manual resolution exists if the provider cannot prove outcome.

### 6.7 Sticky escalation

After a human takes ownership or the ticket reaches `needs_rep`:

- later customer messages append and notify;
- the configured policy determines whether a fresh agent draft is allowed;
- an autonomous send does not silently restart by default;
- ownership/history remain visible.

## 7. Quality and safety evaluation

### 7.1 Shadow-mode evaluation set

Before policy/unrestricted auto-send is recommended, evaluate at least:

- representative WISMO variants;
- delayed/lost/delivered/partial/multi-package states;
- order-not-found and multiple-match cases;
- multiple languages used by the pilot;
- angry or legally sensitive messages;
- refund/cancellation requests outside WISMO;
- prompt injection and malicious links;
- stale/missing connector data;
- duplicate/out-of-order events.

Record:

- classification accuracy;
- correct order-link rate;
- factual support rate;
- unnecessary escalation rate;
- unsafe/unsupported action-proposal rate;
- edit distance or reviewer disposition;
- reopen/complaint rate after live enablement;
- trace completeness.

No single model confidence score is a release gate by itself.

### 7.2 Release threshold

The pilot owner defines business quality thresholds, but these technical thresholds are
mandatory:

- zero cross-store/account executions in the adversarial suite;
- zero duplicate supported side effects under retry/race tests;
- zero plaintext secret findings in logs/traces/results;
- 100% verified trace coverage for supported Ecom-OS reply actions;
- every ambiguous provider timeout enters reconciliation;
- every live auto-send can be located from ticket and Activity pages.

## 8. Analytics definitions

Operational dashboards use versioned definitions.

### Customer service

- inbound tickets/messages;
- agent-run count;
- drafts proposed;
- human-approved sends;
- policy/unrestricted sends;
- escalations;
- time to first response;
- resolution/reopen rate;
- edit/reject rate;
- failed/unknown actions;
- backlog age.

### Autonomy

- actions by mode/tool/store;
- approval rate/time;
- policy pass/fail reason;
- unrestricted grant inventory and changes;
- incident and compensation rate by mode.

### Trace quality

- verified/observed/imported/unknown spans;
- unlinked Hermes events;
- missing prompt/config/policy versions;
- action-to-provider-evidence coverage;
- trace ingest lag.

Definitions, windows, exclusions, and source freshness are visible.

## 9. Accessibility and responsive behavior

Core workflows meet WCAG 2.2 AA intent:

- semantic landmarks and headings;
- keyboard-operable navigation, tables, dialogs, approvals, and chat;
- visible focus;
- screen-reader labels/live regions for streamed updates without excessive chatter;
- contrast and non-color status cues;
- reduced motion;
- no hover-only essential information;
- money/time/coverage labels expressed in text.

Desktop is the primary v1 operations target. Tablet layouts remain usable. Mobile supports
read/triage/approval/chat essentials, but full dense trace analysis may use a focused
responsive view rather than desktop parity.

## 10. Performance and scale test profile

Test with at least:

- 100,000 messages;
- 20,000 tickets;
- 50,000 orders;
- 1,000,000 trace spans/tool/evidence rows combined;
- 10,000 actions/attempts;
- 90 days of metric snapshots;
- a queue burst of 1,000 inbound events;
- multiple concurrent chat and ticket runs within the expected small-team profile.

Required targets follow `03-ENGINEERING.md`. Trace search and ticket queues must use
measured indexes; large raw payloads are not loaded into list pages.

## 11. Pilot release gates

### Gate A — Architecture

- [ ] Slice 0 conformance and restore spikes pass.
- [ ] No supported code path writes Hermes private SQLite.
- [ ] Exact release/version compatibility is recorded.

### Gate B — Data integrity

- [ ] Durable ingress, jobs, outbox, and event replay pass.
- [ ] Store/account identity is explicit everywhere.
- [ ] Migrations pass N-1 realistic-data tests.

### Gate C — Trace and actions

- [ ] Supported tool calls/actions are verified and searchable.
- [ ] Idempotency/race/timeout/reconciliation tests pass.
- [ ] Coverage gaps are visible.

### Gate D — Product workflow

- [ ] Main chat resumes Hermes sessions and uses Ecom-OS tools.
- [ ] WISMO shadow and approval scenarios pass.
- [ ] Sticky escalation passes.
- [ ] Daily brief reconciles and delivers natively.

### Gate E — Security and operations

- [ ] Auth/RBAC/channel mappings are tested.
- [ ] Secret scanning/log tests pass.
- [ ] Backup/restore drill passes.
- [ ] Emergency pause and incident workflow are tested.
- [ ] Production health/alerts are configured.

### Gate F — Owner sovereignty

- [ ] The UI clearly distinguishes business policy from technical integrity.
- [ ] Unrestricted grants execute without undocumented business caps.
- [ ] Every unrestricted change/action remains audited and traced.
- [ ] Direct non-Ecom Hermes capability limitations are disclosed, not hidden.

## 12. Post-v1 candidates

After the pilot gates and production evidence:

- refund execution with exact approval/unrestricted semantics;
- returns/exchanges;
- additional stores and inboxes for the same brand;
- marketing/ad write tools;
- merchandising and product publishing;
- supplier/fulfilment workflows;
- semantic document search provider;
- richer Ecom-OS plugin API;
- advanced anomaly detection;
- cross-instance agency console as a separate management plane;
- mobile/PWA enhancements.

A candidate enters the roadmap only with a trace, action, recovery, identity, and data
source design—not merely a page mockup.
