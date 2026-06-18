# Current Repository Baseline

This is a launch aid, not a substitute for each agent's own audit. The repository will
continue moving; agents record exact paths and commit SHA in their living docs.

## Existing stack at programme design time

- Next.js 16 / React 19 / TypeScript frontend.
- Tailwind, Radix primitives, Framer Motion, TanStack Query/Table, Recharts, cmdk.
- Vitest/Testing Library and Cypress.
- Python 3.12 FastAPI backend with SQLAlchemy/SQLModel, Alembic, Postgres 16.
- Current worker topology includes Redis/RQ; v2 targets Postgres leased jobs.
- Current source retains openclaw-mission-control ancestry and legacy paths.
- Existing Ecom-OS work includes CS tickets/flows/prompts, tasks, analytics/overview,
  connectors, deployment scripts, and an initial Hermes Tool Gateway `/delegate` path.

## How agents use this baseline

- Verify, do not assume, every listed capability at the recorded baseline SHA.
- Preserve passing tests and useful product behavior unless the accepted specs explicitly
  supersede it.
- Prefer adapters/facades and vertical migrations to repository-wide renames.
- Mark old modules `canonical`, `compatibility facade`, `deprecated`, or `unverified` in
  the owning living docs.
- Do not let an old README or old invariant override v2 owner sovereignty, Hermes peer
  integration, trace/action requirements, or the Postgres job decision.
