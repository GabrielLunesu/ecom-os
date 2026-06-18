# Integration Queue

| Order | Branch/PR | Owner | Contract dependencies satisfied | Tests/evidence | Open P0/P1 | Decision |
|---:|---|---|---|---|---|---|
| 1 | Documentation/coordination checkpoint on `agent/a00-orchestrator`, published via `coordination/program` alias | A00 | n/a | Required reading complete; branch/SHA verified at `3909904`; launch report inspected on `origin/main` | RF-001 | Docs-only checkpoint is usable; branch-map docs still need reconciliation |
| — | Observed builder branches `agent/a01-foundation` through `agent/a09-integration` | A01–A09 | Not yet published | No branch diff beyond baseline; local unpublished living-doc diffs exist for A01/A03/A05/A06 only | RF-002, RF-003, RF-004, RF-005 | Not eligible |
| — | `feat/ecom-os-slice-1-design-system` | Unknown/legacy | Conflicts with active v2 programme docs | Deletes prompts, programme living docs, builder living docs, design docs, and many backend modules relative to `3909904` | RF-006 | Reject as active integration candidate unless manually salvaged by owners |
| — | `feat/ecom-os-slice-2-connections` | Unknown/legacy | Conflicts with active v2 programme docs | Deletes prompts, programme living docs, builder living docs, design docs, and multiple migrations/tests relative to `3909904` | RF-006 | Reject as active integration candidate unless manually salvaged by owners |

## Current collision hot spots

| Area | Collision risk | Designated owner/resolver | Current state |
|---|---|---|---|
| Branch names and worktree lookup | Prompts/docs name `agent/A0X-*` and `coordination/program`; observed local branches use lowercase legacy names | Human launch owner / A09 for integration mechanics | Open finding RF-001 |
| Legacy feature branches | Old branches delete active v2 coordination and living-doc structure | A00 rejects for queue; A09 if manually salvaging | Open finding RF-006 |
| Shared contract registry | All agents need trace/action/identity/UI contracts before implementation | A01/A02/A03/A06 by owned interface; A00 audits | Registry is proposed-only |
| Unpublished local interface requests | A01/A03/A05/A06 local docs name requests not yet accepted centrally | Requesting builder + owning interface agent; A00 tracks | Added to `INTERFACE-REQUESTS.md` as observed local requests |
| Global routers/navigation/lockfiles/compose | Multiple route/domain owners will need central registration | A01/A06/A09 | No requests accepted yet |
