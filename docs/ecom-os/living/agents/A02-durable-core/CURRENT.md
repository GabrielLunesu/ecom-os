---
owner: A02
branch: agent/A02-durable-core
status: not_started
last_verified_commit: SET_ME
---

# A02 — Durable Events, Jobs, Traces, and Actions — Current State

## Mission

Build the Postgres durable operational core: inbox/outbox, leased jobs, traces, actions, evidence, incidents, reconciliation primitives, and Activity surfaces.

## Ownership

**Owns:** events, Postgres jobs, traces/runs/spans/tool invocations, actions/attempts/state history, evidence/audit/incidents, trace search tools and Activity/trace/incident routes.

**Does not own:** provider adapters, business-specific CS policy, Hermes transports, metric formulas, deployment files.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes A01 identity/common contracts and A06 UI. Exposes trace/action/job ports to A03–A09.
