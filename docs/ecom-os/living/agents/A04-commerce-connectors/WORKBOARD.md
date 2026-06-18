# A04 — Commerce Connectors and Read Models — Workboard

## Implemented and verified

- **Connector ports + exact binding + typed errors** (`errors.py`, `binding.py`, `ports.py`). Wrong-account/default/latest rejected closed. ✅ tests
- **Provider-independent registry + adapters** (`registry.py`, `adapters/{shopify,inbox,fake}.py`). Composio is one adapter; `composio/store` fails closed. ✅ tests
- **Signed raw-body webhooks + durable inbox** (`webhooks.py`, `durable.py`). Verify→durable insert→dedup-once; invalid signature never persisted. ✅ tests
- **Normalized commerce models + migration** (`models.py`, `a04commerce01`). 11 tables; minor-unit money; provider refs separate. ✅ migration N-1 round-trip
- **Sync engine + read repository** (`sync.py`, `read_repository.py`). Idempotent upsert; order by id/customer with evidence; outage→stale last-good. ✅ tests
- **Durable write path + reconciliation** (`actions.py`). Action digest + intent key, attempts, `outcome_unknown`, reconcile; duplicate-once. ✅ tests
- **Read tools + message events + commerce read API** (`tools.py`, `events.py`, `api.py`). ✅ tests

Evidence: `VERIFICATION.md` — 33 A04 tests + full suite (578 passed) green; mypy/ruff clean.

## Now

- Final checkpoint: commit coherent slice; set `CURRENT.md last_verified_commit`. → verify: clean `git status` and recorded SHA.

## Next (integration-dependent)

- Swap `LocalDurableInbox`/`LocalDurableActionStore` for A02's canonical inbox/action ports when they land (IR-A04-01). Keep the same uniqueness guarantees.
- Register commerce router + read-tool manifest centrally (A01/A09 / A03) (IR-A04-02, IR-A04-05).
- Build `/orders`,`/customers`,connection-settings React pages on A06 primitives (IR-A04-04).
- Migrate the legacy email ingress (`api/ecom_webhooks.py`) onto `connectors/webhooks.py`; remove inbox first-ACTIVE discovery call sites (A05 integration).
- Add a live Shopify write/reconcile conformance fixture, then enable adapter writes (I-19).

## Blocked

- None hard-blocked. Integration steps above depend on A02/A06/A03 contracts (all `proposed`); built behind typed local ports + fakes per OPERATING-PROTOCOL §5.

## Exit condition

Branch acceptance (handoff) is met in code + tests (see `VERIFICATION.md` acceptance table). Remaining for `ready_for_integration`: A02/A06/A03 contracts accepted and the local stand-ins swapped; central registration done; UI pages on A06 primitives.
