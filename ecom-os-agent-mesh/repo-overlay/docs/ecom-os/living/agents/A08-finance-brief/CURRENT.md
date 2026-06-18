---
owner: A08
branch: agent/A08-finance-brief
status: not_started
last_verified_commit: SET_ME
---

# A08 — Finance, Metric Evidence, and Daily Brief — Current State

## Mission

Build deterministic estimated contribution margin, metric snapshots/evidence, Finance surfaces, and idempotent daily briefs narrated/delivered through Hermes when available.

## Ownership

**Owns:** economics inputs/normalization above connector layer, formulas/versioning/snapshots/components, finance tools/page, daily brief snapshot/narration/delivery intent and UI widgets.

**Does not own:** LLM calculation, connector account selection, native channel implementation, global UI, accounting-profit claims.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes A01 common money/time, A02 traces/jobs/actions, A03 narration/channel transport, A04 commerce sources, A06 UI. Exposes brief/metric context to A07.
