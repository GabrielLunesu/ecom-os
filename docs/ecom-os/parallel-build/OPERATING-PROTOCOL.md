# Universal Agent Operating Protocol

Every A00–A09 prompt incorporates this protocol by reference.

## 1. Read before changing code

Read, in order:

1. root `AGENTS.md`;
2. every normative file in `docs/ecom-os/specs/` in its documented reading order;
3. every file in `docs/ecom-os/parallel-build/`;
4. all files in `docs/ecom-os/living/00-program/`;
5. `CURRENT.md` and `INTERFACES.md` for every agent;
6. your own handoff and complete living-doc directory;
7. the current source, tests, migrations, and Git history relevant to your domain.

Do not rely on old README claims when they conflict with v2. Treat working code as
migration input and verify behavior before deleting or replacing it.

## 2. Work in isolation

- Use the assigned branch and a separate worktree.
- Never run two builders in the same worktree.
- Do not edit files owned by another agent.
- Do not force-push a branch another process uses.
- Push coherent checkpoints so A00 and A09 can inspect them.

## 3. First output is a current-state model

Before implementation, update your living documents with:

- what already exists and is reusable;
- target architecture and a Mermaid diagram;
- owned files and files you will not touch;
- contracts you expose and consume;
- ordered workboard;
- current blockers, risks, and edge cases;
- verification plan.

This is not a speculative essay. Cite concrete code paths and tests.

## 4. Living docs are not logs

- Rewrite them to describe current truth; do not append daily journals.
- Keep only open blockers and current risks.
- Replace stale test results with the latest verified evidence.
- Move lasting rationale into an ADR; move behavior into product/operator docs.
- When a task is complete, describe the implemented capability and its code/test links,
  not a dated narrative of how it was built.

## 5. Interface changes

Before creating a cross-domain dependency:

1. check `INTERFACE-REGISTRY.md`;
2. add a precise request to `INTERFACE-REQUESTS.md` if absent;
3. provide a proposed schema, caller, owner, failure semantics, and versioning impact;
4. continue with a typed local port/fake when possible;
5. do not create a second competing contract.

The owning agent accepts or rejects the request in the registry/request document. A00
reports unresolved collisions but does not decide architecture.

## 6. Shared-file discipline

Global routers, navigation, generated clients, dependency locks, compose files, and
normative docs have designated owners. Domain agents expose a module/router/manifest and
record the required registration. The shared-file owner performs the final registration.

## 7. Implementation discipline

- Build vertical, testable slices; a big mission may produce several focused PRs.
- Preserve trace context, identity, store scope, freshness, and typed errors from the first
  implementation—not as cleanup.
- External writes use the action contract. No direct connector write is acceptable.
- Use feature flags or shadow mode for incomplete workflows.
- Do not block on another agent when a stable port/fake can preserve progress.
- Do not invent unavailable Hermes behavior; capability-probe and degrade explicitly.

## 8. Before marking work ready

Update `VERIFICATION.md` with exact commands and results, list migrations and rollback
behavior, confirm owned acceptance criteria, and set `CURRENT.md` to
`ready_for_integration`. A branch is not ready with an unresolved P0/P1 finding, failing
required test, undocumented interface drift, or stale living docs.
