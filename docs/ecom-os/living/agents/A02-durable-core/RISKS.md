# A02 — Durable Events, Jobs, Traces, and Actions — Current Risks and Edge Cases

| ID | Risk/edge case | Impact | Current mitigation/test | Owner | Status |
|---|---|---|---|---|---|
| A02-R01 | Legacy Redis/RQ queue remains active while v2 requires Postgres leases. | Duplicate or lost work if migrated without compatibility coverage. | Postgres durable ingress and durable board-webhook worker now exist beside existing helpers; `legacy`/`durable`/`dual` worker modes are tested, with `legacy` as rollback. Keep Redis path until A09 compose cleanup. | A02/A09 | open |
| A02-R02 | Existing webhook ingress paths may acknowledge before durable inbox acceptance. | Provider retry/replay cannot reconstruct triggers. | Realtime email webhook and board webhook ingest now persist durable inbox/job rows before scheduling compatibility work or returning 202. Worker rollout selection and rollback behavior are covered by `tests/test_queue_worker_migration.py`. | A02/A05 | open |
| A02-R03 | Existing activity feed could be mistaken for trace coverage. | Operators may see logs/feed rows as complete action evidence. | Legacy feed remains separate; new `/activity/traces` and `/activity/actions` expose only durable trace/action records with coverage labels and role-filtered evidence. Frontend must keep this distinction visible. | A02/A06 | open |
| A02-R04 | Refund and connector paths can execute outside generic action attempts. | External writes may lack `outcome_unknown` and idempotent intent semantics. | A02 supplies generic ActionService; A04/A05 must route provider writes through it. | A02/A04/A05 | open |
| A02-R05 | A01 identity contracts are pending. | Actor/store/connection binding could drift across agents. | Store explicit typed scalar fields now and replace with A01 context types once accepted. | A01/A02 | open |

Delete resolved rows after the durable behavior/test/documentation is in place. This is
not an incident history.
