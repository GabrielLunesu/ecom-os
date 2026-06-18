# Living Documentation

These files describe the **current implementation**, its interfaces, remaining work,
blockers, edge cases, and verification. They are deliberately not changelogs.

## Rules

1. Rewrite current truth instead of appending dated prose.
2. Keep only active blockers and unresolved risks.
3. Link to exact code, schema, tests, PR/commit, and operational evidence.
4. Label diagrams `current` or `target`; remove obsolete diagrams.
5. Replace old verification output when newer evidence exists.
6. Put lasting architectural rationale in an ADR, not here.
7. Put user/operator behavior in durable product/runbook documentation when stable.
8. A living document cannot override root invariants or an accepted spec.

## Per-agent files

- `CURRENT.md` — what exists now, status, ownership, and architecture summary.
- `WORKBOARD.md` — current implemented/now/next/blocked work.
- `INTERFACES.md` — APIs/events/schemas/ports consumed and exposed.
- `RISKS.md` — current blockers, edge cases, and failure modes.
- `VERIFICATION.md` — latest commands, tests, fixtures, and observed results.
- `DIAGRAMS.md` — current and target Mermaid diagrams.
- `HANDOFF.md` — what another engineer needs to continue right now.

A00 owns `00-program/`. Every builder owns only its matching folder under `agents/`.
