# A08 — Finance, Metric Evidence, and Daily Brief — Current Handoff

## Safe continuation point

Implementation checkpoint on branch `agent/a08-ops-briefs`. Required normative docs were
read; current A08 implementation inventory and initial interface plan are in the living
docs. The first source slice adds the deterministic formula core in
`backend/app/metrics/formulas.py` with tests in `backend/tests/test_a08_metric_formulas.py`.
The second source slice adds metric snapshot/component persistence in
`backend/app/metrics/models.py`, metadata discovery in `backend/app/models/__init__.py`,
and migration `backend/migrations/versions/a08_001_metric_snapshots.py`, with tests in
`backend/tests/test_a08_metric_models.py`.
The third source slice adds deterministic snapshot generation and idempotent persistence
helpers in `backend/app/metrics/snapshots.py`, with tests in
`backend/tests/test_a08_metric_snapshot_service.py`.
The fourth source slice adds Finance read/explain models in
`backend/app/metrics/read_models.py`, with tests in
`backend/tests/test_a08_metric_read_models.py`.
The fifth source slice exports an unregistered Finance router in
`backend/app/metrics/api.py`, with direct handler tests in
`backend/tests/test_a08_finance_api.py`.
The sixth source slice exports unregistered metric read tool definitions/handlers in
`backend/app/metrics/tools.py`, with tests in `backend/tests/test_a08_metric_tools.py`.
The seventh source slice adds a degraded legacy Shopify order source bridge in
`backend/app/metrics/legacy_sources.py`, with tests in
`backend/tests/test_a08_legacy_sources.py`.
The eighth source slice adds deterministic daily brief snapshot/fallback primitives in
`backend/app/metrics/briefs.py`, daily brief/delivery-intent records in
`backend/app/metrics/models.py`, migration coverage in
`backend/migrations/versions/a08_001_metric_snapshots.py`, and tests in
`backend/tests/test_a08_daily_briefs.py`.
The ninth source slice extends the unregistered Finance router and tool exports with
daily brief generate/get plus delivery-intent status/ensure handlers in
`backend/app/metrics/api.py` and `backend/app/metrics/tools.py`, with tests in
`backend/tests/test_a08_finance_api.py` and
`backend/tests/test_a08_daily_brief_tools.py`.
The tenth source slice adds `BriefCardSummary` read output and unregistered card-summary
handlers for A07 Today and Finance UI consumption in `backend/app/metrics/read_models.py`
and `backend/app/metrics/api.py`, with coverage in
`backend/tests/test_a08_finance_api.py`.
The eleventh source slice adds narration-result and delivery-result recording for A03
callbacks in `backend/app/metrics/briefs.py`, `backend/app/metrics/api.py`, and
`backend/app/metrics/tools.py`, with fallback/status/evidence coverage in
`backend/tests/test_a08_daily_briefs.py`,
`backend/tests/test_a08_finance_api.py`, and
`backend/tests/test_a08_daily_brief_tools.py`.
The twelfth source slice adds a local read-only `/finance` route in
`frontend/src/app/(ecom)/finance/page.tsx`, typed A08 finance calls in
`frontend/src/lib/ecom-api.ts`, and tests in
`frontend/src/app/(ecom)/finance/page.test.tsx`. The route requires exact store scope,
renders formula/evidence/drilldown details, and visibly degrades while the A08 backend
router remains unmounted.
The thirteenth source slice adds local drilldown routes at
`frontend/src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.tsx` and
`frontend/src/app/(ecom)/finance/daily-briefs/[briefId]/page.tsx`, shared presentation
helpers in `frontend/src/app/(ecom)/finance/finance-ui.tsx`, id-based typed hooks in
`frontend/src/lib/ecom-api.ts`, and route tests under each drilldown folder. The routes
refuse missing ids, expose formula guardrails, evidence, metric refs, delivery intents,
attempt count, errors, trace refs, and `outcome_unknown` without inferring latest/default
records.
The fourteenth source slice adds deterministic daily brief composition in
`backend/app/metrics/brief_composer.py`, with coverage in
`backend/tests/test_a08_daily_brief_composer.py`. The composer creates the economics
section from a persisted metric snapshot read model, carries metric/component/source/trace
evidence into brief items, rejects caller-provided economics overrides, and lets missing
CS/action/incident/task/research/health inputs become explicit unavailable sections.
The fifteenth source slice adds idempotent daily brief generation from one exact metric
snapshot in `backend/app/metrics/brief_generation.py`, exported through
`POST /finance/daily-briefs/generate-from-metric` and
`ecom.daily_brief.generate_from_metric`. It validates brand/store/reporting
date/timezone/snapshot scope, rejects mismatches instead of falling back to latest/default,
and persists the composed brief without sending native channel messages.
The sixteenth source slice adds A03-facing delivery dispatch packets in
`backend/app/metrics/read_models.py`, exported through
`GET /finance/daily-brief-delivery-intents/{intent_id}/dispatch-packet` and
`ecom.daily_brief.delivery_intent.dispatch_packet.get`, with tests in
`backend/tests/test_a08_daily_brief_delivery_packet.py`. Packets include body text,
intent/current body hash comparison, idempotency key, target, trace/evidence, guardrails,
and `dispatch_allowed`/`dispatch_status`. They allow only pending/failed matching-body
intents and block delivered, outcome_unknown, and body-hash mismatch states.
The seventeenth source slice adds the local delivery packet UI route at
`frontend/src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.tsx`,
extends `frontend/src/lib/ecom-api.ts` with packet types/hooks, and links daily brief
delivery intents to the packet route. It shows dispatch allowed/blocked state, body hash
comparison, idempotency key, body text, guardrails, evidence, warnings, and trace without
sending any channel message.
The eighteenth source slice adds `MetricCardSummary` in
`backend/app/metrics/read_models.py` and unregistered metric card API handlers in
`backend/app/metrics/api.py`. The card gives A07 Today and compact Finance UI consumers a
deterministic exact-snapshot summary with value, formula version, reporting window,
coverage/freshness, missing components, warnings, trace, component count, and detail link.

## What is working

- Legacy `/api/v1/ecom/metrics` returns Shopify order-derived revenue, orders, AOV, and
  unavailable reasons for session/funnel metrics.
- Legacy `/api/v1/metrics/dashboard` returns task/approval/activity dashboard analytics
  with focused tests.
- Prototype Overview/Analytics pages render legacy KPIs and unavailable states.
- Store connection references and Shopify `list_orders` read path exist as migration
  inputs.
- A08 formula core computes estimated contribution margin from signed components using
  integer minor units, ISO currency, coverage/freshness, source precedence, FX basis and
  attribution metadata, and timezone-aware local-day reporting windows.
- A08 metric records persist formula version, reporting window/timezone, integer value,
  coverage/freshness, missing components, warnings, trace ref, component contribution,
  source timestamps, and evidence refs; the unique window/formula constraint protects
  snapshot idempotency.
- A08 snapshot service generates formula snapshots through a local source port and
  reuses an existing persisted snapshot for the same store/metric/formula/window/currency,
  preserving the original trace and avoiding duplicate components.
- A08 read/explain models expose persisted snapshots with component evidence and coverage
  details, plus narration guardrails that prohibit recalculation and profit mislabeling.
- A08 metric card output exposes compact persisted-snapshot status for A07/Finance UI:
  value, formula version, reporting window, coverage/freshness, missing inputs, warnings,
  trace, component count, and detail link.
- A08 Finance router handlers return latest snapshot, metric card summaries, snapshot
  detail, and explain context over the read models. They are not mounted in
  `backend/app/main.py`; A01/A09 own central registration and A03 owns generated tool
  catalog registration.
- A08 metric tools `ecom.metric.get` and `ecom.metric.explain` return structured result
  envelopes with evidence, freshness, warnings, and no action/approval IDs. They are not
  registered globally; A03 owns final catalog generation.
- A08 legacy Shopify source bridge adapts existing `list_orders` payloads into partial
  `net_sales` components with integer minor units and order evidence refs. It rejects
  mixed currencies and keeps all unavailable cost, fee, refund/chargeback, ad, shipping,
  and FX inputs as formula coverage gaps.
- A08 daily brief primitives generate a deterministic snapshot over all runtime-spec
  default sections, fill unavailable sections with missing/unavailable coverage, render a
  deterministic fallback body, hash the body, persist brief snapshots idempotently by
  brand/store/date/timezone/revision, and persist Hermes-native delivery intents
  idempotently by stored brief/channel target.
- A08 daily brief API/tool handlers can generate/read stored briefs, read delivery
  status, and ensure a pending delivery intent. They do not mount/register globally and do
  not call native channel transports.
- A08 card summary output exposes compact daily brief status for A07/Finance UI: status,
  reporting window, coverage/freshness, narration status, delivery status/counts, trace,
  warnings, metric snapshot refs, and detail link.
- A08 narration-result recording preserves deterministic fallback text when Hermes
  narration fails or is unavailable. A08 delivery-result recording stores status,
  evidence, error, trace, delivered timestamp, and attempt count for an existing
  delivery intent. These callbacks do not perform native channel sends.
- A08 local `/finance` UI renders deterministic estimated contribution margin snapshots,
  component evidence, coverage/freshness, warnings, daily brief fallback text, narration
  status, and delivery intent status from the A08 read models. It refuses aggregate scope
  and does not substitute legacy KPI totals when the A08 API is empty or unmounted.
- A08 local Finance drilldowns render exact persisted metric snapshots and daily briefs
  by id. The brief detail exposes delivery intent retry/failure state, including
  `outcome_unknown`, and links referenced metric snapshots.
- A08 daily brief composition now derives the economics section from metric snapshot
  evidence instead of requiring callers to hand-build the finance section.
- A08 daily brief API/tools can now generate a stored deterministic brief from persisted
  metric evidence through the exact-scope generation-from-metric path.
- A08 can now hand A03 a read-only dispatch packet for a delivery intent without
  performing the native channel send itself.
- A08 local Finance UI now renders the delivery packet detail for a single exact intent,
  including blocked retry/reconciliation state and body hash mismatch visibility.

## What remains

- See `WORKBOARD.md` for the ordered A08 slices.
- Do not claim `ready_for_integration` until `make backend-migration-check` completes in
  an environment with Docker, `scripts/ci/branch_readiness.py` exists and prints READY,
  and the programme decides whether to fix or exempt the non-A08 baseline formatting
  files listed in `VERIFICATION.md`.
- Register/mount the local Finance UI/backend route through A06/A09/A01, then wire
  accepted A03 Hermes narration/native delivery callbacks to the exported A08 handlers.
- Replace local source fakes with accepted A04/A02 ports when available.

## Blockers and decisions

- No architectural decision request is currently needed; existing specs cover A08.
- Current blockers are accepted interfaces from A01, A02, A03, A04, A06, and A07. They
  are listed in `RISKS.md` and `INTERFACES.md`.

## Commands to resume

```bash
git status --short --branch
cd backend && uv run --extra dev python -m pytest tests/test_a08_metric_formulas.py tests/test_a08_metric_models.py tests/test_a08_metric_snapshot_service.py tests/test_a08_metric_read_models.py tests/test_a08_finance_api.py tests/test_a08_metric_tools.py tests/test_a08_legacy_sources.py tests/test_a08_daily_briefs.py tests/test_a08_daily_brief_composer.py tests/test_a08_daily_brief_generation.py tests/test_a08_daily_brief_delivery_packet.py tests/test_a08_daily_brief_tools.py tests/test_metrics_ranges.py tests/test_metrics_kpis.py tests/test_metrics_filters.py
cd backend && uv run --extra dev python -m ruff check app/metrics app/models/__init__.py tests/test_a08_metric_formulas.py tests/test_a08_metric_models.py tests/test_a08_metric_snapshot_service.py tests/test_a08_metric_read_models.py tests/test_a08_finance_api.py tests/test_a08_metric_tools.py tests/test_a08_legacy_sources.py tests/test_a08_daily_briefs.py tests/test_a08_daily_brief_composer.py tests/test_a08_daily_brief_generation.py tests/test_a08_daily_brief_delivery_packet.py tests/test_a08_daily_brief_tools.py
cd backend && uv run --extra dev python -m mypy app/metrics
cd backend && uv run --extra dev alembic heads
cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false
cd frontend && ./node_modules/.bin/eslint 'src/lib/ecom-api.ts' 'src/app/(ecom)/finance/**/*.tsx'
cd frontend && ./node_modules/.bin/vitest run 'src/app/(ecom)/finance/page.test.tsx' 'src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.test.tsx' 'src/app/(ecom)/finance/daily-briefs/[briefId]/page.test.tsx' 'src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.test.tsx' --coverage.enabled=false
rg -n "profit|revenue|margin|contribution|metric|brief|daily|currency|money|COGS|cogs|ad spend|ROAS|roas" backend frontend
```

## Do not accidentally regress

- Do not label v1 numbers as audited/accounting profit; use estimated contribution
  margin.
- Do not let Hermes or any LLM calculate/source finance or brief numbers.
- Do not treat missing COGS/ad/fees/shipping/FX as zero coverage.
- Do not call Slack/Telegram/email/etc directly from A08; native delivery is A03/Hermes.
- Preserve explicit unavailable states from legacy KPIs while replacing float totals with
  v2 snapshots.
- Keep source/evidence/freshness/coverage visible on every mutable KPI and brief number.
