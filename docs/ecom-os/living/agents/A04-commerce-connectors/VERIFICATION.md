# A04 — Commerce Connectors and Read Models — Verification

## Latest verified commit

`agent/a04-cs` checkpoint (commit recorded in `CURRENT.md` `last_verified_commit`).

## Required checks

| Check | Command/fixture | Result | Evidence |
|---|---|---|---|
| Static/type checks | `uv run mypy app/connectors` | **pass** | `Success: no issues found in 18 source files` |
| Lint/format | `uv run ruff check app/connectors` | **pass** | `All checks passed!` (black + isort applied) |
| A04 unit/contract tests | `uv run pytest tests/test_a04_*.py` | **pass** | `33 passed` |
| Full regression suite | `uv run pytest` | **pass** | `578 passed, 1 xfailed in 474s` (no regressions) |
| Migration upgrade/rollback (N-1) | `alembic stamp a0b1c2d3e4f5 → upgrade head → downgrade a0b1c2d3e4f5` | **pass** | 11 commerce tables created on upgrade; 0 after downgrade; version transitions `a0b1c2d3e4f5 ↔ a04commerce01` |
| Migration graph integrity | `uv run python scripts/check_migration_graph.py` | **pass** | `OK: migration graph integrity passed`; single head `a04commerce01` |

## Acceptance scenarios (handoff Ready-for-integration) — all covered by tests

| Acceptance criterion | Test | Status |
|---|---|---|
| Real/sandbox order retrieved by ID and by customer with source/freshness/evidence | `test_a04_sync_readmodel.py::test_order_retrieved_by_id_and_customer_with_evidence` | ✅ |
| Duplicate webhook/provider event changes normalized state once | `test_a04_webhook_inbox.py::test_duplicate_webhook_accepted_once`; `test_a04_sync_readmodel.py::test_duplicate_event_changes_state_once` | ✅ |
| Wrong connection/store/account fails closed with traced reason | `test_a04_binding_registry.py::test_registry_wrong_account_fails_closed` / `..._fake_adapter_rejects_wrong_account_on_read`; `test_a04_action_reconcile.py::test_wrong_account_write_fails_closed` | ✅ |
| Outage returns last-good marked stale/partial, not fabricated current | `test_a04_sync_readmodel.py::test_outage_returns_last_good_marked_stale` | ✅ |
| Ambiguous provider outcome reconciled via the action contract | `test_a04_action_reconcile.py::test_timeout_after_acceptance_reconciles_without_duplicate` / `..._reports_absent_side_effect` | ✅ |
| No raw managed OAuth token stored as ordinary data | `Connection` stores `account_ref`/`secret_handle` references only; `Secret` redaction retained (existing `test_connector_invariants.py`) | ✅ |
| Invalid webhook signature never enters the stream | `test_a04_webhook_inbox.py::test_invalid_signature_never_persisted` | ✅ |
| Read tools are read-only with evidence envelopes | `test_a04_tools_events_api.py::test_read_tool_manifest_is_read_only` / `..._read_tools_return_evidence_envelopes` | ✅ |
| Normalized inbox/message events emitted once (untrusted) for A05 | `test_a04_tools_events_api.py::test_inbox_events_emitted_once_and_untrusted` | ✅ |
| Commerce read API renders ok/degraded/404 states | `test_a04_tools_events_api.py::test_commerce_api_orders_and_not_found` | ✅ |

## Known gaps (declared, not hidden)

- Live Shopify **write/reconcile** path is declared unsupported in the adapter
  (`supports_reconciliation=False`) pending a live-conformance fixture (I-19); the
  durable write/reconcile vertical is fully exercised via the fake adapter.
- A02 durable inbox/action ports are stood in locally (`commerce_provider_events`,
  `commerce_actions`); swap to A02's canonical tables at integration (IR-A04-01).
- Orders/Customers React pages depend on A06 primitives (IR-A04-04); the backend read
  API + read tools that power them are complete and tested.
