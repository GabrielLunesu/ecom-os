# Current Dependency Map

The target dependency graph is in `../../parallel-build/TEAM-TOPOLOGY.md`. This file shows
only current unresolved dependencies.

| Consumer | Provider | Needed interface/deliverable | State | Blocking? | Evidence |
|---|---|---|---|---|---|
| A02–A09 | A01 | Identity, request context, common money/time/error/ID contracts, route registration convention | Local ready-for-integration claim, not published to `origin` | Blocks integration beyond isolated fakes | A01 local full backend suite passed `628 passed, 1 xfailed`; ruff/mypy pass; no `origin/agent/a01-foundation` ref observed |
| A03–A08 | A02 | Trace context, tool invocation, durable action, job/event ports | Local durable-core/webhook/activity/queue-worker draft, not published | Blocks verified tool/action integration | A02 local `backend/app/{actions,events,jobs,traces}/**`, `api/{ecom_webhooks,board_webhooks,activity}.py`, `services/{queue_worker,webhooks/dispatch}.py`, models, migration `a02d1e2f3a4b`, migration verifier, and focused tests; targeted tests passed `40 passed`; focused ruff/mypy pass |
| A05/A07/A08 | A03 | HermesBridge session/run/channel contracts and capability model | Local commit `00242ca`, not published; owner docs stale; programme-file ownership collision; real conformance gate RED until endpoint supplied | Blocks Hermes-backed workflows and native delivery | A03 local targeted tests passed `97 passed`; focused ruff/mypy pass; no real Hermes probe |
| A05/A08 | A04 | Exact-bound commerce/order/customer/inbox read models and connector ports | Local source draft, not published | Blocks CS and finance source evidence | A04 local targeted binding/read-model/webhook/action/API tests passed `33 passed`; A02 event/action ports still absent |
| All route owners | A06 | UI token/component/state contract | Local commit `a9d870a`, not published; owner docs stale; programme-file ownership collision | Blocks final UI integration, but route owners can use local placeholders | A06 committed theme/mobile/state/component-lab/card/a11y primitives; typecheck passed; Vitest passed `150 passed`; A06-owned eslint passed; whole-project eslint fails in A07-owned brand page |
| A09 | All builders | Ready branches with tests, migrations, accepted interfaces, and current living docs | Not available; local readiness tooling exists but has static failures | Blocks integration queue | Only A00 refs are published on `origin`; A09 branch-readiness tool reports all builders NOT READY; A01/A03/A04/A06/A09 commits and A02/A05/A07/A08 diffs are local only |
| A05 | A02/A04 | Reply/discount/refund action executor plus exact connector attempt/reconciliation ports | Not published | Blocks any external CS write integration | Baseline `backend/app/services/flow_engine.py` sends email and creates discounts directly |
| A04/A05 | A01/A04 | Exact store/connection/account binding and channel identity | Not published | Blocks connector writes and CS automation | Baseline `backend/app/services/cs_loop.py` selects `stores[0]`; inbox discovery returns first active mail account |
| A01 | A02 | Audit/trace sink for identity/config changes | Requested locally, not accepted | Blocks production-grade audited identity/admin changes; A01 can use no-op test fake for discovery | Local A01 `INTERFACES.md` diff names `AuditTraceSink` |
| A03 | A01/A02 | Service identity, WebSocket request context, trace/run/tool-invocation envelope and ingest | Requested locally, not accepted | Blocks real Hermes chat/tool correlation | Local A03 `INTERFACES.md` diff names A01/A02 requests |
| A06 | A02/A04/A05/A07/A08 | Durable action/trace/evidence shapes, entity-summary shape, and metric/KPI freshness/coverage shape | Requested locally, not accepted | Blocks final entity/action/trace/KPI card contracts; local fakes allowed | Local A06 `INTERFACES.md` and A06 programme-file diff name A02/A04/A05/A07/A08 dependencies; IR-026 added for entity summary |
| A04 | A02/A03/A01 | Durable inbox/action/event ports, tool catalog registration, common types/client workflow | Requested locally, not accepted | Blocks connector webhook/read-tool integration | Local A04 `INTERFACES.md` names these dependencies |
| A07 | A02/A03/A05/A08/A06 | Ask-Hermes launch, tool registration, trace/evidence refs, CS attention source, brief/metric source, UI states | Requested locally, not accepted | Blocks Today/tasks/knowledge integration | Local A07 `INTERFACES.md` names these dependencies |
| A08 | A02/A03/A04/A07/A06/A09 | Economics source port, trace/evidence/jobs, narration/channel delivery, task/research inputs, `/finance` route/nav | Requested locally, not accepted; broader backend regression currently fails | Blocks finance and daily brief integration | Local A08 `INTERFACES.md` names these dependencies; A00 observed daily-brief tool manifest/test mismatch |
| A09 | A01/A02/A04/A05/A07/A08/A09 | Migration graph from local implementation drafts | Not accepted | Blocks any integration of new migrations | Branch-local heads observed: A01 `a01_0001_identity`, A02 `a02d1e2f3a4b`, A04 `a04commerce01`, A05 `a05i2f7c0007`, A08 `a08_001_metric_snapshots`, A09 `a09c1d2e3f40`; A07 draft revises older `e2f9c6b4a1d3` |
| A08 | A01 | Shared Money type / money wire shape | Conflict observed locally | Blocks finance integration until reconciled | A01 defines `app.core.money.Money(minor_units,currency)`; A08 defines `app.metrics.formulas.Money(minor,currency)` |

## Current critical path

The current critical path is branch/contract establishment, then accepted A01 and A06 foundations,
then accepted A02 trace/action/job primitives. A03, A04, A05, A08, and A07 can audit and
build typed local ports/fakes, but no feature branch is merge-ready until its consumed
interfaces are accepted and its living docs contain exact verification evidence. CS
automation must remain fenced or shadow/proposal/execution-fake-only until accepted A02
action/trace and A04 exact-binding ports exist. The next programme risks are uncoordinated
local interface design, stale local owner docs, and unpublished implementation drafts:
A01/A03/A04/A05/A06/A07/A08 now name concrete requests locally, while
A01/A02/A03/A04/A05/A06/A07/A08/A09 have source/config/test evidence that is not visible
through `origin` and not yet migration-graph or integration-gate verified. Fresh A00 checks
also show A08 has a failing broader backend regression and A09's new readiness tool has
ruff/mypy failures.
