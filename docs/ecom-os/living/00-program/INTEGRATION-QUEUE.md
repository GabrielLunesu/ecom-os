# Integration Queue

| Order | Branch/PR | Owner | Contract dependencies satisfied | Tests/evidence | Open P0/P1 | Decision |
|---:|---|---|---|---|---|---|
| 1 | Documentation/coordination checkpoint on `agent/a00-orchestrator`, published via `coordination/program` alias | A00 | n/a | Required reading complete; branch/SHA verified at `3909904`; launch report inspected on `origin/main` | RF-001 | Docs-only checkpoint is usable; branch-map docs still need reconciliation |
| — | `agent/a01-foundation` local commit `4fa6bc0` | A01 | Not yet published to `origin`; consumed contracts not accepted | Docs-only discovery checkpoint inspected locally | RF-001, RF-007 | Not eligible until pushed and dependencies/verification mature |
| — | `agent/a09-integration` local commit `1e71b0d` | A09 | Not yet published to `origin`; integration gate not open | CI/security gate commit inspected locally; import-boundary script passed | RF-001, RF-007 | Not eligible until pushed; A09 should prepare gates, not integrate domains yet |
| — | Local worktree diff on A01 | A01 | Not yet published; consumed contracts not accepted | Shared type/error draft inspected; targeted test passed | RF-001, RF-007, RF-009, RF-010 | Not eligible |
| — | Local worktree diffs on A03/A04/A06 | A03/A04/A06 | Not yet published; programme-doc collisions for A03/A04; consumed contracts not accepted | A03 tool catalog/bridge tests passed; A04 connector binding tests passed; A06 UI lint inconclusive | RF-001, RF-007, RF-008, RF-009 | Not eligible |
| — | Local implementation drafts on A05/A07/A08 | A05/A07/A08 | Not yet published; consumed contracts not accepted; migration graph not verified | A05 lifecycle/lease tests passed; A07 operator workspace tests passed; A08 metric tests passed | RF-002, RF-003, RF-005, RF-007, RF-009, RF-010 | Not eligible |
| — | Local System health draft on `agent/a09-integration` | A09 | Not yet published; integration gate not open | `/system/health` route/service/schema inspected; targeted tests passed | RF-001, RF-007, RF-009 | Not eligible |
| — | `feat/ecom-os-slice-1-design-system` | Unknown/legacy | Conflicts with active v2 programme docs | Deletes prompts, programme living docs, builder living docs, design docs, and many backend modules relative to `3909904` | RF-006 | Reject as active integration candidate unless manually salvaged by owners |
| — | `feat/ecom-os-slice-2-connections` | Unknown/legacy | Conflicts with active v2 programme docs | Deletes prompts, programme living docs, builder living docs, design docs, and multiple migrations/tests relative to `3909904` | RF-006 | Reject as active integration candidate unless manually salvaged by owners |

## Current collision hot spots

| Area | Collision risk | Designated owner/resolver | Current state |
|---|---|---|---|
| Branch names and worktree lookup | Prompts/docs name `agent/A0X-*` and `coordination/program`; observed local branches use lowercase legacy names | Human launch owner / A09 for integration mechanics | Open finding RF-001 |
| Legacy feature branches | Old branches delete active v2 coordination and living-doc structure | A00 rejects for queue; A09 if manually salvaging | Open finding RF-006 |
| Shared contract registry | All agents need trace/action/identity/UI contracts before implementation | A01/A02/A03/A06 by owned interface; A00 audits | Registry is proposed-only |
| Unpublished local interface requests | A01/A03/A04/A05/A06/A07/A08 local docs name requests not yet accepted centrally | Requesting builder + owning interface agent; A00 tracks | Added to `INTERFACE-REQUESTS.md` as observed local requests |
| Programme living docs | Builders A03/A04/A08 edited A00-owned `docs/ecom-os/living/00-program/**` locally | A00 owns central files; builders own their own folders | Open finding RF-008; A00 reconciled requests here |
| Alembic migration graph | Local A05/A07/A08 draft migrations can create branch/merge pressure | A09 merge owner; domain migration owner for each revision | A05 and A08 both revise `a0b1c2d3e4f5`; A07 revises older `e2f9c6b4a1d3`; no integration until graph tested |
| Money value type | A01 and A08 both define Money shapes | A01 owns common type; A08 consumes after acceptance | Open finding RF-010 |
| Global routers/navigation/lockfiles/compose | Multiple route/domain owners will need central registration | A01/A06/A09 | No requests accepted yet |
