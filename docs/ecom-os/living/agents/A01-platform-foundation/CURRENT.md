---
owner: A01
branch: agent/A01-platform-foundation
status: not_started
last_verified_commit: SET_ME
---

# A01 — Platform Foundation and Identity — Current State

## Mission

Establish the shared production skeleton, identity model, request context, typed contracts, and migration conventions that every domain uses.

## Ownership

**Owns:** auth and bootstrap; users/roles/service identities/channel identity records; common IDs/money/time/error types; API contract generation; central route registration; shared backend dependency lock.

**Does not own:** event/action internals, Hermes transport, commerce sync, CS workflows, UI primitives, deployment topology.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes normative specs only initially. Exposes identity/request/contract foundations to A02–A09.
