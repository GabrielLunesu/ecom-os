# A08 — Finance, Metric Evidence, and Daily Brief — Workboard

## Implemented and verified

- Repository audit completed at `3909904`; no v2 A08 domain implementation exists yet.
- Legacy metrics inventory documented in `CURRENT.md`.
- Versioned estimated contribution margin formula core added in
  `backend/app/metrics/formulas.py` with integer minor units, ISO currency,
  timezone-aware reporting windows, source precedence, coverage/freshness warnings, FX
  basis metadata, attribution-window metadata, and component reconciliation.
- Metric snapshot/component persistence added in `backend/app/metrics/models.py` and
  `backend/migrations/versions/a08_001_metric_snapshots.py`, including component
  evidence refs and a window/formula uniqueness constraint for idempotent snapshots.
- Deterministic snapshot generation/persistence service added in
  `backend/app/metrics/snapshots.py` with a local `ContributionComponentSource` port and
  idempotent persistence behavior.
- Finance read/explain models added in `backend/app/metrics/read_models.py` for
  snapshot retrieval, component drilldown, coverage display, and narration guardrails.
- Unregistered Finance router exported in `backend/app/metrics/api.py` for latest
  snapshot, snapshot detail, and explain-context handlers.
- `MetricCardSummary` read model and unregistered API handlers added for A07 Today and
  compact Finance UI consumption. The summary exposes exact snapshot id, value, formula
  version, reporting window, coverage/freshness, missing components, warnings, trace,
  component count, and a detail link without falling back to legacy KPI totals.
- Unregistered metric tool definitions/handlers exported in `backend/app/metrics/tools.py`
  for A03 tool-catalog registration: `ecom.metric.get` and `ecom.metric.explain`.
- Degraded legacy Shopify order source bridge added in
  `backend/app/metrics/legacy_sources.py`; it feeds partial `net_sales` into the A08
  source port with integer minor units and order evidence refs while leaving missing
  cost, fee, refund, ad, shipping, and FX components visible.
- Deterministic daily brief snapshot/fallback primitives added in
  `backend/app/metrics/briefs.py`, with `daily_briefs` and
  `daily_brief_delivery_intents` persistence in `backend/app/metrics/models.py` and
  `backend/migrations/versions/a08_001_metric_snapshots.py`. The local slice covers all
  default sections, unavailable-section warnings, fallback body hashing, immutable
  snapshot idempotency, and delivery-intent idempotency.
- Unregistered daily brief API/tool handlers added in `backend/app/metrics/api.py` and
  `backend/app/metrics/tools.py` for brief generate/get and delivery-intent status/ensure.
  They persist or read Ecom-OS internal records only and do not call native channel
  transports.
- `BriefCardSummary` read model and unregistered card-summary API handlers added for A07
  Today and Finance UI consumption. The summary exposes brief status, reporting window,
  coverage/freshness, narration status, delivery status/counts, trace reference, warnings,
  metric snapshot refs, and a detail link without editing A06/A09-owned navigation.
- Narration-result and delivery-result recording added in `backend/app/metrics/briefs.py`,
  `backend/app/metrics/api.py`, and `backend/app/metrics/tools.py`. Failed or unavailable
  narration keeps the deterministic fallback body as final text; delivery callbacks record
  status, evidence, error, trace, delivered timestamp, and attempt count without sending a
  channel message.
- Local `/finance` route added in `frontend/src/app/(ecom)/finance/page.tsx`, with typed
  read-model calls in `frontend/src/lib/ecom-api.ts` and tests in
  `frontend/src/app/(ecom)/finance/page.test.tsx`. It requires exact store scope, renders
  deterministic estimated contribution margin evidence/drilldowns, shows daily brief
  fallback/narration/delivery-intent status, and visibly degrades while the A08 backend
  router remains unmounted.
- Local drilldown routes added at
  `frontend/src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.tsx` and
  `frontend/src/app/(ecom)/finance/daily-briefs/[briefId]/page.tsx`, with shared Finance
  UI helpers in `frontend/src/app/(ecom)/finance/finance-ui.tsx`. They read exact snapshot
  and brief ids only, expose formula guardrails, component evidence, metric refs,
  fallback text, delivery intents, attempts, errors, `outcome_unknown`, and trace refs,
  and do not infer latest/default records.
- Local delivery packet route added at
  `frontend/src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.tsx`.
  Daily brief details link each intent to its packet. The packet page reads one exact
  intent, shows dispatch allowed/blocked status, body hash comparison, idempotency key,
  body text, guardrails, evidence, warnings, and trace state without sending a channel
  message.
- Daily brief composer added in `backend/app/metrics/brief_composer.py`, with tests in
  `backend/tests/test_a08_daily_brief_composer.py`. It creates economics sections from
  persisted metric snapshots, carries metric/component/trace/source evidence into the
  brief, rejects caller-provided economics overrides, and fills non-economics gaps as
  explicit unavailable sections rather than zeroes.
- Daily brief generation-from-metric service added in
  `backend/app/metrics/brief_generation.py`, with tests in
  `backend/tests/test_a08_daily_brief_generation.py`. The unregistered API and tool
  surfaces now expose exact metric-backed generation through
  `POST /finance/daily-briefs/generate-from-metric` and
  `ecom.daily_brief.generate_from_metric`, validating brand/store/date/timezone/snapshot
  scope before idempotent persistence.
- A03-facing delivery dispatch packet added in `backend/app/metrics/read_models.py`, with
  API/tool exports and tests in `backend/tests/test_a08_daily_brief_delivery_packet.py`.
  It gives A03 the exact body, body hash, idempotency key, target, evidence, trace, and
  guardrails for Hermes-native delivery while blocking delivered, outcome_unknown, and
  body-hash-mismatch dispatch.
- Operator-visible behavior note added at
  `docs/changes/2026-06-19-a08-finance-brief.md`.
- Targeted tests pass for A08 formulas, persistence, snapshot service, read/explain
  models, Finance handlers, metric tools, legacy source bridge, daily brief primitives,
  daily brief composer/generation, daily brief API/tools, card summary output,
  narration-failure fallback, delivery packet/result visibility, the local Finance
  summary/detail/packet routes, and existing dashboard metrics.

## Now

- Branch is pushed-ready once external readiness blockers clear: Docker-backed
  `make backend-migration-check`, missing `scripts/ci/branch_readiness.py`, and full
  repository format gates currently failing on non-A08 baseline files. A08-owned backend
  and Finance frontend checks pass.

## Next

1. Request/accept A06/A09 registration for `/finance` navigation and the A01/A09 backend
   mount for `backend/app/metrics/api.py`.
2. Wire accepted A03 Hermes narration/native-delivery callbacks to the exported handlers.
3. Hand off the exported `MetricCardSummary` and `BriefCardSummary` contracts to A07,
   then adapt to any accepted Today input naming changes.

## Blocked

- `make backend-migration-check` cannot complete locally because Docker is unavailable.
- `scripts/ci/branch_readiness.py` is absent from this worktree, so the requested READY
  self-check cannot run.
- Full repo format gates fail on non-A08 baseline files; A08-owned files are formatted.
- No accepted A01 money/time/identity contract yet.
- No accepted A02 trace/evidence/job/action primitives yet.
- No accepted A04 normalized commerce/economics source port yet.
- No accepted A03 narration/channel/cron delivery port yet.
- No accepted A06 navigation registration or A01/A09 backend route mount for `/finance`
  yet. The local route file exists but remains unlinked and degrades against the unmounted
  API.

## Exit condition

Branch is ready only when Build Spec Slice 10 and Slice 11 acceptance criteria pass:
formula fixtures reconcile every displayed KPI to components/evidence; missing/stale
COGS/ad/fee/FX inputs reduce visible coverage; timezone/window boundaries are tested;
Finance UI and tools expose formulas, freshness, coverage, and drilldowns; daily brief
numbers reconcile to deterministic sources; narration failure falls back deterministically;
one native delivery path is idempotent, visible, retryable, and trace-linked.
