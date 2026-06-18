---
owner: A06
branch: agent/A06-design-system
status: not_started
last_verified_commit: SET_ME
---

# A06 — Design System and Application Shell — Current State

## Mission

Extract the complete reusable design language from dashboard-inspo and establish the shadcn/Radix source of truth, themes, shell, primitives, patterns, and component lab.

## Ownership

**Owns:** global frontend layout, sidebar/nav, theme/tokens, UI primitives, command palette, page/state patterns, design docs and component lab.

**Does not own:** domain business logic, backend workflows, multi-tenant data semantics, domain-specific route ownership.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes dashboard-inspo and product specs. Exposes UI contracts to every route owner.
