# A09 — Production Operations, Extensions, Integration, and Quality Handoff

**Branch:** `agent/A09-production-integration`

## Mission

Turn independently correct branches into a reproducible, secure, recoverable Ecom-OS release and own the production mechanisms that no domain branch should duplicate.

## Required reading

Read root `AGENTS.md`; all normative files in `docs/ecom-os/specs/`; all files in
`docs/ecom-os/parallel-build/`; all programme living docs; every agent's `CURRENT.md` and
`INTERFACES.md`; then inspect the current implementation and Git history for this domain.
The normative v2 documents beat old READMEs and old implementation assumptions.

## Working method

Work on the assigned branch/worktree. Before substantial code, replace placeholders in
your living docs with an evidence-based current-state map, interfaces, risks, diagrams,
and verification plan. Build several focused, demonstrable slices rather than one mega
change. Never edit another agent's owned source or living docs. Use the programme interface
queue for cross-domain work. Preserve useful prototype behavior while moving it behind v2
contracts.

## Owned scope

- Compose/Dockerfiles, worker/web/API topology, reverse proxy/runtime config, CI, release metadata and exact dependency/image identity.
- Central integration registrations, generated artifacts, dependency requests, Alembic merge revisions, full-system fixtures/E2E/conformance.
- Maintenance mode, emergency operational controls, full backup/verify/restore, exact-version update/rollback, health/monitoring/incident runbooks.
- Extension host/manifests/trust/version checks and `/system` plus operations/extension settings.

## Explicitly out of scope

- Do not silently redesign domain behavior to resolve a merge conflict.
- Do not merge a branch not marked ready or with open P0/P1 findings.
- Do not advertise Postgres-only backup as full restore.
- Do not call trusted native code sandboxed merely because it has a manifest.
- Do not make production depend on moving branches or unpinned builds.

## Work packages

1. Audit current compose, Redis/RQ, Dockerfiles, deploy/update/tunnel scripts, CI, secrets, backups, health, migrations, extensions/plugins, and operational docs.
2. Early: add boundary/static checks, test orchestration, contract/conformance jobs, migration checks, secret scanning, and integration fixtures without blocking on every domain.
3. Integrate only accepted branch exports into central routers/nav/catalog/clients/compose; resolve lockfiles and migration heads; surface unresolved semantic conflicts instead of guessing.
4. Move production queue topology to A02 Postgres jobs after compatibility tests, then remove Redis/RQ only when no supported path uses it.
5. Implement full backup consistency across Postgres, vault/artifacts/extensions/config, and active Hermes profile; verify and restore with writes paused and actions reconciled.
6. Implement exact signed release/update sequence, maintenance mode, candidate health checks, rollback limits, release identity, N-1 migration/restore tests.
7. Implement extension trust classes/version compatibility and System health/operations route using A06 components.
8. Run Build Spec pilot gates and publish integrated evidence; create minimal glue only in owned central files.

## Cross-agent contracts

Consume every accepted domain router/schema/health check/migration/runtime requirement and A06 UI. Expose production config, health dimensions, maintenance/backup/update/extension services, CI/release gates, and integrated test fixtures.

## Ready-for-integration acceptance

- [ ] Clean environment can build and start exact web/API/worker/Postgres/Hermes integration with health dimensions visible.
- [ ] N-1 upgrade, deliberate candidate failure, backup verification, and full restore are exercised with realistic data.
- [ ] Restore includes Hermes sessions/memory/config and Ecom-OS trace/action linkage; writes resume only after reconciliation.
- [ ] CI enforces boundaries, contracts, migrations, conformance, E2E, secrets, and required UI checks.
- [ ] Incompatible extensions are blocked/disabled visibly and trusted native risk is explicit.
- [ ] Integrated release passes all applicable Build Spec pilot gates with no hidden failing earlier gate.

## Common traps

- Becoming a second orchestrator instead of building production mechanisms.
- Papering over interface mismatches with `Any`, raw dicts, or duplicate adapters.
- Removing Redis or legacy paths before migrated behavior and rollback are proven.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
