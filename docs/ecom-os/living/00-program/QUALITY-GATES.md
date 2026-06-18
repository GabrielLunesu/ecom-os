# Current Quality Gates

| Gate | Owner(s) | Required evidence | Current state | Blocking gap |
|---|---|---|---|---|
| Normative docs and boundary rules | A00/A01 | source-of-truth audit | A00 reading complete at `3909904`; baseline shortcut audit started | Builder placeholder docs; baseline code still has v2 shortcut risks |
| Branch/worktree identity | A00/A09 | branch map matching launch instructions and integration docs | degraded | RF-001: `origin/main` launch docs confirm observed branches, but this branch's normative parallel docs still name older branches |
| Hermes protocol/conformance spike | A03/A09 | conformance output | pending | No A03 evidence |
| Durable event/trace/action core | A02 | idempotency, lease, outcome tests | pending | No A02 evidence; baseline writes bypass durable action/trace |
| Exact connector binding/reconciliation | A04 | wrong-account and timeout fixtures | pending | No A04 evidence; baseline picks first store/active inbox in CS loop |
| Design system/source extraction | A06 | catalog, component lab, accessibility | pending | No A06 evidence |
| WISMO shadow workflow | A05 | evaluation set and trace links | pending | No A05 evidence; baseline CS sends are not action-ledger backed |
| Finance evidence | A08 | formula and coverage fixtures | pending | No A08 evidence |
| Full restore/update | A09 | restore drill | pending | No A09 evidence |
| Migration graph | A09/A02 | Alembic heads and N-1 upgrade evidence | partial baseline evidence | `uv run alembic heads` reports one head `a0b1c2d3e4f5`; no N-1 upgrade fixture evidence |
| Baseline high-risk tests | A00/owners | Targeted test evidence for existing shortcut paths | partial baseline evidence | `uv run --extra dev pytest tests/test_connector_invariants.py tests/test_ticket_ingestion.py tests/test_refund_path.py -q` passed 23 tests with SQLAlchemy connection-cleanup warnings; these tests prove old prototype invariants only, not v2 gates |
| Builder worktree drift | A00 | Current sibling worktree status | checked | A01/A03/A05/A06 now have local uncommitted living-doc diffs; all builder worktrees remain at `3909904`; no implementation code evidence yet |
| Builder local living-doc progress | A00 | Local sibling worktree status and diffs | partial local evidence | A01/A03/A05/A06 have uncommitted living-doc diffs; A02/A04/A07/A08/A09 remain placeholder-only. Local diffs are not integration evidence until committed/pushed by owners. |

This table reflects current gate status, not release history.
