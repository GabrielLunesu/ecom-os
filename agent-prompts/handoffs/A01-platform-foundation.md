# A01 — Platform Foundation and Identity Handoff

**Branch:** `agent/A01-platform-foundation`

## Mission

Create the stable shared floor: repository convergence, owner bootstrap, human/service/channel identity, authorization context, common types, typed errors, API contracts, health primitives, and migration conventions.

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

- `backend/app/auth/**`, shared core/common domain modules, owner/bootstrap APIs and UI, central API registration.
- `packages/contracts/**` or the repository-equivalent canonical generated contract package.
- Backend shared dependency/lock changes and generated API client workflow.
- Identity/config administrative audit integration through an A02 port/fake until available.

## Explicitly out of scope

- Do not implement the durable queue/action/trace internals (A02).
- Do not speak raw Hermes protocols (A03), call providers (A04), implement CS/metrics/tasks, or own deployment files (A09).
- Do not perform a wholesale directory rename that breaks the functioning prototype.

## Work packages

1. Audit current local/Clerk auth, models, schemas, API generation, errors, health, migrations, and shared utilities.
2. Define UUID/time/money/store-scope/request/actor/trace context types and the versioned API error envelope.
3. Implement owner bootstrap that closes after creation; users, roles, role permissions, service identities, and channel-identity records with server-side enforcement.
4. Create request context propagation and recent-auth hooks for high-risk changes; secrets remain handles/redacted values.
5. Establish contract generation and domain-router registration patterns that let other agents export modules without editing central files.
6. Publish migration naming/head protocol, shared fixtures, and the base identity migrations.
7. Retain local auth only as an explicit development/self-hosted mode with documented limits.

## Cross-agent contracts

Expose authenticated ActorContext, RequestContext, StoreScope, Money, typed Error, service identity verification, channel identity lookup, and contract-generation hooks. Consume A02 audit/trace sink when available and provide a no-op/test port beforehand.

## Ready-for-integration acceptance

- [ ] Owner bootstrap closes after first owner and cannot be replayed anonymously.
- [ ] Unauthorized HTTP/socket/page operations fail server-side.
- [ ] Role, service, and channel identity fixtures cover allowed and denied paths.
- [ ] No secret is serialized, logged, or stored as ordinary plaintext data.
- [ ] Common contracts generate strict frontend types and are used by at least one real endpoint.
- [ ] Migration and restart tests pass against realistic seeded prototype data.

## Common traps

- Building a second business authorization engine instead of identity/permission primitives.
- Letting API handlers accumulate domain orchestration.
- Editing every old model before a vertical migration proves the new boundary.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
