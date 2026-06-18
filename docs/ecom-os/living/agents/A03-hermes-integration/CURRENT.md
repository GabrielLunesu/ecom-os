---
owner: A03
branch: agent/A03-hermes-integration
status: not_started
last_verified_commit: SET_ME
---

# A03 — Hermes Native Integration and Main Chat — Current State

## Mission

Integrate Ecom-OS with Hermes as an independent peer using supported protocols, canonical Hermes sessions, generated tools, native channels, cron, and conformance probes.

## Ownership

**Owns:** HermesBridge, capability negotiation, TUI/API/background transports, adapter/MCP package, tool catalog framework, session mapping, chat and Agents routes, channel/cron transport interfaces.

**Does not own:** direct Hermes SQLite/profile mutation, operational business truth, CS policy, finance calculation, global UI primitives.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes A01 identity, A02 trace/action invocation, A06 UI. Exposes run/session/channel contracts to A05/A07/A08.
