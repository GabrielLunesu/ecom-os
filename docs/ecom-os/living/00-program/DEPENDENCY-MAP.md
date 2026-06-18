# Current Dependency Map

The target dependency graph is in `../../parallel-build/TEAM-TOPOLOGY.md`. This file shows
only current unresolved dependencies.

| Consumer | Provider | Needed interface/deliverable | State | Blocking? | Evidence |
|---|---|---|---|---|---|
| A02–A09 | A01 | Identity, request context, common money/time/error/ID contracts, route registration convention | Not published | Blocks integration beyond isolated fakes | A01 `CURRENT.md` and `INTERFACES.md` are placeholders at `3909904` |
| A03–A08 | A02 | Trace context, tool invocation, durable action, job/event ports | Not published | Blocks verified tool/action integration | A02 `CURRENT.md` and `INTERFACES.md` are placeholders at `3909904` |
| A05/A07/A08 | A03 | HermesBridge session/run/channel contracts and capability model | Not published | Blocks Hermes-backed workflows and native delivery | A03 `CURRENT.md` and `INTERFACES.md` are placeholders at `3909904` |
| A05/A08 | A04 | Exact-bound commerce/order/customer/inbox read models and connector ports | Not published | Blocks CS and finance source evidence | A04 `CURRENT.md` and `INTERFACES.md` are placeholders at `3909904` |
| All route owners | A06 | UI token/component/state contract | Not published | Blocks final UI integration, but route owners can use local placeholders | A06 `CURRENT.md` and `INTERFACES.md` are placeholders at `3909904` |
| A09 | All builders | Ready branches with tests, migrations, accepted interfaces, and current living docs | Not available | Blocks integration queue | All builder branches observed at baseline with no ready evidence |
| A05 | A02/A04 | Reply/discount/refund action executor plus exact connector attempt/reconciliation ports | Not published | Blocks any external CS write integration | Baseline `backend/app/services/flow_engine.py` sends email and creates discounts directly |
| A04/A05 | A01/A04 | Exact store/connection/account binding and channel identity | Not published | Blocks connector writes and CS automation | Baseline `backend/app/services/cs_loop.py` selects `stores[0]`; inbox discovery returns first active mail account |

## Current critical path

The current critical path is branch/contract establishment, then A01 and A06 foundations,
then A02 trace/action/job primitives. A03, A04, A05, A08, and A07 can audit and build
typed local ports/fakes, but no feature branch is merge-ready until its consumed
interfaces are accepted and its living docs contain exact verification evidence. CS
automation must remain fenced or shadow-only until A02 action/trace and A04 exact-binding
ports exist.
