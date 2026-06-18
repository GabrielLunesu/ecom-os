---
owner: A04
branch: agent/A04-commerce-connectors
status: not_started
last_verified_commit: SET_ME
---

# A04 — Commerce Connectors and Read Models — Current State

## Mission

Build exact-bound connector adapters, signed ingestion, synchronization, normalized commerce read models, freshness/evidence, and Orders/Customers surfaces.

## Ownership

**Owns:** connection records and adapters, webhook verification, Shopify/inbox synchronization, stores/orders/customers/products and provider references, Orders/Customers/connection-settings routes and read tools.

**Does not own:** ticket workflow/policy, durable action internals, Hermes transport, finance definitions, deployment secrets infrastructure.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes A01 identity/contracts, A02 jobs/traces/actions, A06 UI. Exposes commerce/connector ports to A05/A08.
