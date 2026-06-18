# Ecom-OS — Documentation

> **Document set:** v2.0 architecture baseline  
> **Status:** pre-build, normative  
> **Last reviewed:** 2026-06-18  
> **Hermes compatibility baseline:** Hermes Agent v0.16.0 / `v2026.6.5`

Ecom-OS is a self-hosted ecommerce operating system for one brand. It is a separate
application that **integrates with Hermes Agent through Hermes's supported interfaces**.
Hermes remains the agent runtime, conversation system, memory system, scheduler, and
messaging gateway. Ecom-OS provides the ecommerce data plane, workflows, dashboards,
connectors, action execution, and trace ledger that make Hermes useful for operating a
store.

Ecom-OS is not a fork, reskin, or replacement for Hermes. It does not patch Hermes core
or treat Hermes as a library that Ecom-OS owns. The two products run side by side and are
upgraded independently.

## The three load-bearing principles

1. **Hermes-native integration.** The main chat, sessions, memory, skills, tools, cron,
   and native channels remain Hermes-native. Ecom-OS connects through programmatic
   chat protocols, official hooks, plugins, MCP, and the messaging gateway.
2. **Owner sovereignty.** The owner chooses how much autonomy an agent receives,
   including an explicit unrestricted mode. Ecom-OS provides safe defaults and clear
   consequences, but it does not permanently trap the operator inside platform policy.
3. **Traceability before mythology.** Every Ecom-OS run, decision, tool call, approval,
   action attempt, connector result, and business outcome is linked into a searchable
   trace. The operator and Hermes can inspect what happened later and distinguish agent
   judgment, prompt/configuration, external data, connector behavior, and human action.

## Reading order

| Order | Document | Purpose |
|---:|---|---|
| 1 | [`00-VISION.md`](00-VISION.md) | Product thesis, users, principles, success criteria, and scope. |
| 2 | [`01-ARCHITECTURE.md`](01-ARCHITECTURE.md) | System boundaries, service topology, data ownership, and runtime flows. |
| 3 | [`02-TECH-DECISIONS.md`](02-TECH-DECISIONS.md) | Architectural decisions and their consequences. |
| 4 | [`03-ENGINEERING.md`](03-ENGINEERING.md) | How the system is built, tested, observed, and changed. |
| 5 | [`04-DATA-AND-TRACEABILITY.md`](04-DATA-AND-TRACEABILITY.md) | Canonical event, run, action, audit, and trace model. |
| 6 | [`05-OPERATIONS-AND-SECURITY.md`](05-OPERATIONS-AND-SECURITY.md) | Deployment, credentials, updates, backups, incidents, and recovery. |
| 7 | [`ECOM-OS-RUNTIME-SPEC.md`](ECOM-OS-RUNTIME-SPEC.md) | Normative Hermes integration and agent execution contract. |
| 8 | [`ECOM-OS-BUILD-SPEC.md`](ECOM-OS-BUILD-SPEC.md) | Product surfaces, build order, acceptance tests, and release gates. |
| 9 | [`AGENTS.md`](AGENTS.md) | Non-negotiable rules for any coding agent or contributor. |
| — | [`DOCUMENTATION-CHANGELOG.md`](DOCUMENTATION-CHANGELOG.md) | What changed from the original design and why. |

## Source-of-truth hierarchy

When documents conflict, apply this precedence:

1. `AGENTS.md` invariants.
2. Accepted ADRs in `02-TECH-DECISIONS.md`.
3. `ECOM-OS-RUNTIME-SPEC.md` and `ECOM-OS-BUILD-SPEC.md`.
4. `01-ARCHITECTURE.md`, `04-DATA-AND-TRACEABILITY.md`, and
   `05-OPERATIONS-AND-SECURITY.md`.
5. `00-VISION.md`.
6. `03-ENGINEERING.md` conventions.

A later ADR may supersede an earlier ADR. It must name the superseded decision. Code and
documentation may not silently disagree; the same change set must update one or the
other.

## Architecture in one paragraph

A single-brand Ecom-OS instance runs a web app, API, workers, and Postgres beside one
primary Hermes profile. The Ecom-OS dashboard talks to Hermes through Hermes's
programmatic integration protocol; Hermes calls ecommerce capabilities through the
Ecom-OS Hermes adapter or the Ecom-OS MCP server. Shopify, inbox, advertising, payment,
and supplier integrations sit behind connector adapters. Durable inbound events are
normalized into Postgres, agent work becomes a trace, and external writes become
idempotent actions with recorded attempts and outcomes. Hermes's own session history,
memory, skills, cron jobs, and channel routing stay in the Hermes profile and are backed
up as Hermes state rather than copied into Ecom-OS.

## Ownership of state

| State | Canonical owner |
|---|---|
| Agent conversations, session history, model/session metadata | Hermes `state.db` and Hermes APIs |
| Curated agent/user memory, SOUL, skills, cron, gateway config | Hermes profile |
| Orders, tickets, customers, tasks, metrics, policies, approvals | Ecom-OS Postgres |
| Ecom-OS events, traces, actions, attempts, evidence, incidents | Ecom-OS Postgres |
| Brand documents and SOP source files | User-space document vault; indexed metadata in Ecom-OS |
| Connector OAuth tokens | Connector provider or secret store; references in Ecom-OS |
| Ecom-OS application secrets | Runtime secret store or environment, never database plaintext |

Hermes memory is used for durable agent knowledge and operator preferences. It is not a
replacement for live store state. The agent obtains current orders, tickets, metrics,
policies, and traces through Ecom-OS tools.

## Glossary

- **Hermes profile:** the dedicated Hermes state boundary for the brand.
- **Run:** one interactive turn or background agent execution.
- **Trace:** the linked record of a run and its steps.
- **Span:** one step inside a trace, such as retrieval, model call, tool call, or action.
- **Action:** an intended external side effect, such as sending a reply or issuing a
  refund.
- **Attempt:** one connector request made while completing an action.
- **Event:** an immutable fact accepted by Ecom-OS.
- **Audit record:** an administrative or configuration change made by a human or agent.
- **Policy:** optional owner-defined business rules for autonomous writes.
- **System invariant:** technical integrity behavior that remains active in every
  autonomy mode, such as identity binding, idempotency, secret redaction, and tracing.
- **Integration adapter:** the thin Hermes-side package that exposes Ecom-OS tools and
  forwards supported lifecycle telemetry. It contains no ecommerce source of truth.

## Hermes compatibility policy

The baseline was verified against the official Hermes Agent documentation and the latest
release available on 2026-06-18. Ecom-OS pins a tested Hermes range and probes runtime
capabilities at startup. Feature availability is negotiated; undocumented Hermes
internals are never assumed to be stable.

Primary upstream references:

- [Hermes release history](https://github.com/NousResearch/hermes-agent/releases)
- [Programmatic integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration)
- [Session storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage)
- [Persistent memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [MCP integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
- [Plugins and event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)
- [Scheduled tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [Messaging gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)

## Repository expectation

The final repository should keep these documents under `docs/` and a short root
`README.md` should link here. `AGENTS.md` remains at the repository root so building
agents load it automatically.
