# Current Quality Gates

| Gate | Owner(s) | Required evidence | Current state | Blocking gap |
|---|---|---|---|---|
| Normative docs and boundary rules | A00/A01 | source-of-truth audit | A00 reading complete at `3909904`; baseline shortcut audit started | Builder placeholder docs; baseline code still has v2 shortcut risks |
| Branch/worktree identity | A00/A09 | branch map matching launch instructions and integration docs | degraded | RF-001: `origin/main` launch docs confirm observed branches, but this branch's normative parallel docs still name older branches |
| Hermes protocol/conformance spike | A03/A09 | conformance output | local docs only | A03 local audit classifies OpenClaw gateway as pattern-only and `/delegate` as obsolete; no v2 bridge/conformance code |
| Durable event/trace/action core | A02 | idempotency, lease, outcome tests | pending | No A02 evidence; baseline writes bypass durable action/trace |
| Exact connector binding/reconciliation | A04 | wrong-account and timeout fixtures | pending | No A04 evidence; baseline picks first store/active inbox in CS loop |
| Design system/source extraction | A06 | catalog, component lab, accessibility | local docs/design docs only | A06 has local `docs/ecom-os/design/**` diffs; no component lab/tests published |
| WISMO shadow workflow | A05 | evaluation set and trace links | local first invariant draft | A05 local ticket lifecycle tests exist, but no accepted A02/A03/A04 ports and baseline CS sends are not action-ledger backed |
| Finance evidence | A08 | formula and coverage fixtures | local first formula draft | A08 local metric formula tests exist, but no accepted economics source/trace/job contracts and no published branch |
| Full restore/update | A09 | restore drill | local docs only | A09 local commit inventories gaps; no restore/update implementation |
| Migration graph | A09/A02 | Alembic heads and N-1 upgrade evidence | partial baseline evidence plus local draft risk | `uv run alembic heads` in A00 baseline reports one head `a0b1c2d3e4f5`; A05 local migration revises that head, while A07 local migration revises older `e2f9c6b4a1d3` and would need merge-head handling |
| Baseline high-risk tests | A00/owners | Targeted test evidence for existing shortcut paths | partial baseline evidence | `uv run --extra dev pytest tests/test_connector_invariants.py tests/test_ticket_ingestion.py tests/test_refund_path.py -q` passed 23 tests with SQLAlchemy connection-cleanup warnings; these tests prove old prototype invariants only, not v2 gates |
| Builder worktree drift | A00 | Current sibling worktree status | checked | A01/A09 have local docs commits; A03/A04/A05/A06/A07/A08 have uncommitted diffs; only A00 refs are published on `origin` |
| Builder local living-doc progress | A00 | Local sibling worktree status and diffs | partial local evidence | A01/A03/A04/A05/A06/A07/A08/A09 living docs inspected locally; A02 remains placeholder-only. Local/unpublished evidence is not integration evidence until committed and pushed by owners. |
| Programme-doc ownership | A00/builders | No non-A00 edits under `docs/ecom-os/living/00-program/**` | failing locally | A03/A04/A08 worktrees contain local edits to A00-owned programme files; A00 reconciled useful requests here, builders must remove owner-boundary collisions |

This table reflects current gate status, not release history.
