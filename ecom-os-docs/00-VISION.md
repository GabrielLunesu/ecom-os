# 00 — Vision

> **Status:** normative product direction  
> **Last reviewed:** 2026-06-18

## The thesis

Ecom-OS is a **traceable operating system for running one ecommerce brand with Hermes
Agent**.

Hermes is the agent. Ecom-OS is the ecommerce control plane around it: live business
context, operational workflows, dashboards, connectors, action execution, and a durable
record of what happened. The combination should let an operator ask the brand anything,
assign work to the agent, automate repetitive operations, and later inspect every
important decision or side effect.

The product is not built around the fiction that an agent can never make a bad decision.
People make bad decisions, prompts can be poorly written, policies can be wrong, source
data can be stale, and connectors can fail in ambiguous ways. Ecom-OS therefore aims for:

- useful defaults;
- explicit control over autonomy;
- reliable execution semantics;
- complete operational traceability;
- fast inspection, diagnosis, and correction.

The owner may choose strict approvals, bounded autonomy, or full autonomy. The platform
must make that choice legible and attributable, not secretly replace it with paternalistic
rules.

## What we are building

A new instance should give a brand:

1. **One persistent Hermes brain.** The brand's main Hermes profile carries its native
   sessions, memory, skills, personality, scheduler, and messaging channels.
2. **One ecommerce command center.** The web app exposes chat, customer service,
   profit, tasks, activity, traces, connections, agents, and settings.
3. **One live tool surface.** Hermes can query and act on current store data through
   Ecom-OS tools without treating copied prompt context as the source of truth.
4. **One trace graph.** Tickets, messages, model runs, tool calls, approvals, external
   actions, connector attempts, metrics, incidents, and human changes link together.
5. **One proactive communication loop.** Daily briefs, alerts, and completed work are
   delivered through Hermes's configured native channel, such as Slack, Telegram,
   Discord, email, or another supported gateway platform.

## Who it is for

### Primary user

A single-brand operator or small ecommerce team, initially dropshipping-first, who:

- runs one or more storefronts for the same brand;
- spends substantial time on WISMO and repetitive support;
- needs contribution margin rather than vanity revenue;
- wants an agent that can research, answer, operate, and report;
- is willing to run or commission a dedicated self-hosted instance;
- values control, source access, and inspectability.

### Team shape

The first design assumes:

- one owner;
- a small number of operators or customer-service representatives;
- optional finance, marketing, or operations roles;
- one primary shared brand agent;
- optional separate Hermes profiles for private or specialized work.

One brand per instance is a deployment and blast-radius boundary. It is not a claim that
all information must be globally visible to every team member. Founder-private, finance,
and personal surfaces still require explicit access controls or separate Hermes profiles.

## First principles

### 1. Hermes remains native

Ecom-OS must not fork Hermes, duplicate its conversation database, replace its scheduler,
or build a competing messaging gateway. The main chat must feel like Hermes because it
is Hermes: the same sessions, tools, memory, approvals, model switching, and channel
continuity exposed through an Ecom-OS interface.

### 2. Business truth stays live

Orders, tickets, customers, products, costs, advertising data, policies, tasks, actions,
and traces are queried from Ecom-OS and its connectors at the time they are needed. They
are not frozen into the system prompt or trusted merely because they appeared in an old
conversation.

Hermes memory stores durable agent knowledge, user preferences, conventions, and lessons.
It does not become the accounting database or ticket ledger.

### 3. The owner controls the risk envelope

Ecom-OS supports five effective tool modes:

- **Disabled:** the tool is unavailable.
- **Observe:** the tool may read or simulate but cannot create an external side effect.
- **Approve:** every external write waits for an authorized human.
- **Policy:** writes execute autonomously when owner-defined rules pass; otherwise they
  wait, fail, or escalate as configured.
- **Unrestricted:** a granted tool may execute without Ecom-OS business caps or approval.

Unrestricted does not disable technical integrity. The system still binds the exact
store/account, validates the request schema, deduplicates retries, records the action,
redacts secrets, and reconciles uncertain outcomes. An owner may intentionally issue a
large refund; a duplicated webhook must not accidentally issue it twice.

### 4. Traceability is a product surface

A trace is not merely a log file for developers. It is part of the operator experience.
From any ticket, order, KPI, task, daily brief, or chat answer, the user should be able to
open the relevant timeline and see:

- what triggered the work;
- which Hermes session and model handled it;
- what instructions, skill versions, and policy versions applied;
- which evidence and live records were retrieved;
- which tools were called and with what redacted arguments;
- what the model proposed;
- whether a person approved or changed it;
- which connector request ran;
- what the provider reported;
- what the eventual business outcome was;
- whether the trace is complete, observed, or partly outside Ecom-OS visibility.

Hermes itself must receive trace-inspection tools so the operator can ask: “Why did this
happen?”, “Find the first bad discount this month”, or “Compare the failed tickets with
the successful ones.”

### 5. Chat is the universal control surface, not the only surface

The main chat can reach all Ecom-OS domains, open linked entities, explain numbers, start
work, inspect traces, and prepare actions. Structured pages remain essential for scanning,
comparison, queues, bulk work, approvals, and oversight.

Every structured surface should be callable from chat, and every important chat result
should be linkable back to structured data.

### 6. Proactivity must be quiet, useful, and attributable

The system should report without demanding constant dashboard attention. A daily brief
through the user's Hermes home channel should cover:

- yesterday's revenue and estimated contribution margin;
- ROAS and data freshness;
- tickets handled, escalated, reopened, or failed;
- refunds, discounts, cancellations, and unusual writes;
- work completed by research or operations agents;
- tasks due today;
- connector or data-quality problems;
- links to the underlying traces.

Metrics are computed deterministically by Ecom-OS. Hermes may summarize and prioritize
them, but it must not invent the numbers.

### 7. Escape hatches are legitimate product behavior

The supported path is configuration, tools, skills, adapters, and Ecom-OS plugins. The
owner may also edit source, install arbitrary Hermes tools, expose terminal/browser
capabilities, or bypass Ecom-OS entirely. That freedom has consequences:

- core edits may require manual merges;
- direct external actions may be visible only as observed Hermes events or later provider
  state;
- Ecom-OS cannot guarantee complete traces for tools it does not execute or observe;
- the UI must label those limits honestly.

The platform should never claim control it does not possess.

## The core operator experience

### The home page: “What needs my attention?”

The first screen is a living operational brief, not a wall of charts. It shows outcomes,
exceptions, stale data, pending approvals, agent failures, tasks, and unusual behavior.
Each card links to its trace or source records.

### The main chat: “Ask or do anything”

The operator can ask:

- “Why did margin drop yesterday?”
- “Handle the WISMO queue.”
- “Show every refund over €100 this month and explain each one.”
- “Inspect ticket 8142 and tell me whether the agent or my policy was wrong.”
- “Create a task for Sarah to contact the supplier.”
- “Research three competitor offers and save the findings.”

The chat streams Hermes-native tool progress and supports approvals, cancellation,
session history, model changes, and linked trace inspection.

### Customer service: “Automate the repetitive, surface the uncertain”

The inbox provides threaded tickets, live order context, agent drafts, autonomous sends,
human ownership, sticky escalation, and a full timeline. WISMO is the first end-to-end
slice because it is common, measurable, and relatively bounded.

### Profit: “Show contribution, confidence, and freshness”

The product leads with estimated contribution margin rather than revenue. Every figure
states its formula, source coverage, currency, attribution assumptions, and last refresh.
A precise-looking number without evidence is treated as a product defect.

### Activity and traces: “What happened, exactly?”

The trace explorer supports search by date, ticket, customer, order, agent, session,
tool, action, policy, outcome, and incident. It can group thousands of events into runs
and show the exact path from trigger to business result.

## Product principles

- **Trace links everywhere.** Every automation result and mutable KPI should have a path
  to evidence.
- **Current state over copied context.** Query live data at execution time.
- **Owner intent over hidden policy.** Defaults may be conservative; capabilities remain
  configurable.
- **No false certainty.** Show freshness, missing inputs, ambiguous outcomes, and trace
  coverage.
- **One action, one identity.** Every external write names the actor, agent, store,
  connection, and reason.
- **Recovery is part of the workflow.** Retries, reconciliation, replay, and incidents
  are visible product behaviors.
- **Native where Hermes is already strong.** Reuse Hermes sessions, memory, tools,
  channels, cron, profiles, and approvals instead of rebuilding them.
- **Structured where ecommerce needs structure.** Queues, metrics, entities, policies,
  and action ledgers belong in Ecom-OS.
- **Source available and inspectable.** Operators can understand and alter the system
  they rely on.

## v1 scope

The first production release proves the foundation with:

- one brand and one primary Hermes profile;
- one Shopify store;
- one customer-service inbox;
- the Hermes-backed main chat;
- Ecom-OS read tools for orders, tickets, customers, metrics, tasks, and traces;
- durable ingestion and ticket threading;
- WISMO classification, drafting, review, autonomous mode, and sticky escalation;
- external reply sending with idempotency and reconciliation;
- the trace explorer and incident workflow;
- daily briefing through a configured Hermes native channel;
- estimated contribution margin with freshness and missing-data indicators;
- tasks and approvals;
- owner-configurable autonomy, including unrestricted writes;
- tested backup and restore of both Ecom-OS and Hermes state.

## Explicit v1 non-goals

- Multi-tenant SaaS inside one instance.
- A generic workflow builder for every business.
- A marketplace for arbitrary untrusted plugins.
- Full accounting or tax reporting.
- Perfect causal attribution for advertising.
- A replacement for Hermes memory, sessions, channels, cron, or dashboard administration.
- A guarantee that arbitrary terminal/browser/third-party tools are fully traceable.
- Every ecommerce department on day one.
- A mandatory external vector database.
- Pretending autonomous operation is risk-free.

## Success criteria

The product is ready for a real pilot when a new operator can:

1. install Ecom-OS beside a supported Hermes release;
2. connect a store and inbox;
3. open the Ecom-OS chat and resume a real Hermes session;
4. ask for current store facts and receive evidence-linked answers;
5. process WISMO tickets in shadow, approval, policy, or unrestricted mode;
6. open any sent reply or external action and inspect the full trace;
7. ask Hermes to diagnose a failed or suspicious run using trace tools;
8. receive a correct daily brief through the configured Hermes channel;
9. restore the instance from backup without losing authoritative business state or
   Hermes sessions;
10. upgrade Ecom-OS and Hermes independently within the supported compatibility range.

## What failure looks like

The design has failed if:

- the dashboard becomes a second, disconnected agent product;
- Ecom-OS silently copies or edits Hermes's private databases as an integration method;
- users cannot tell why an action occurred;
- a retry can duplicate a side effect;
- an “unrestricted” setting still hides undocumented business caps;
- a direct Hermes capability is presented as if Ecom-OS controls it;
- a daily metric cannot be traced to source data;
- the system requires a bespoke vector stack before it can answer useful questions;
- updates routinely destroy user-space or strand traces from their sessions.
