---
owner: A08
branch: agent/a08-ops-briefs
status: integration_blocked
last_verified_commit: pending-current-commit
---

# A08 — Finance, Metric Evidence, and Daily Brief — Current State

## Mission

Build deterministic estimated contribution margin, metric snapshots/evidence, Finance surfaces, and idempotent daily briefs narrated/delivered through Hermes when available.

## Ownership

**Owns:** economics inputs/normalization above connector layer, formulas/versioning/snapshots/components, finance tools/page, daily brief snapshot/narration/delivery intent and UI widgets.

**Does not own:** LLM calculation, connector account selection, native channel implementation, global UI, accounting-profit claims.

## Current implementation

### Reusable existing assets

- A08 now has a canonical formula-core seed in `backend/app/metrics/formulas.py`, tested by
  `backend/tests/test_a08_metric_formulas.py`. It defines the v1 estimated contribution
  margin formula over integer minor-unit `Money`, explicit ISO currency, local-day
  reporting windows, component signs, source coverage/freshness, source precedence, FX
  basis metadata, attribution-window metadata, warnings, and reconciliation to component
  contributions. UI integration, production source wiring, and daily brief composition
  still need to be built.
- A08 now has persistent metric snapshot/component records in
  `backend/app/metrics/models.py`, imported through `backend/app/models/__init__.py` for
  SQLModel metadata discovery, and migration
  `backend/migrations/versions/a08_001_metric_snapshots.py`. The tables store formula
  version, reporting date/timezone/window, currency, integer minor-unit value,
  coverage/freshness, missing components, warnings, trace reference, component
  contribution, source timestamps, collected timestamps, source refs, and evidence refs.
  `backend/tests/test_a08_metric_models.py` verifies persistence and uniqueness for
  window/formula idempotency.
- A08 now has a deterministic snapshot service in `backend/app/metrics/snapshots.py`,
  tested by `backend/tests/test_a08_metric_snapshot_service.py`. It defines a local
  `ContributionComponentSource` port, generates estimated contribution margin snapshots
  from source components, and persists snapshots idempotently by store, metric, formula,
  window, and currency without duplicating components or overwriting the original trace.
- A08 now has Finance read/explain models in `backend/app/metrics/read_models.py`,
  tested by `backend/tests/test_a08_metric_read_models.py`. They expose persisted
  snapshots as drilldown-ready read models with integer money values, reporting window,
  formula version, coverage, freshness, warnings, trace reference, component
  contributions, source refs, source/collected timestamps, and evidence refs. The same
  module now exposes `MetricCardSummary` for A07 Today and compact Finance UI consumers:
  snapshot id, value, formula version, reporting date/timezone/window, coverage/freshness,
  missing component kinds, warning count/detail, trace reference, component count, and
  detail link. It also exposes `BriefCardSummary` for A07 Today and Finance UI consumers:
  brief status, reporting window, coverage/freshness, narration status, delivery
  status/counts, trace reference, warnings, metric snapshot refs, and detail link.
  `DailyBriefDeliveryPacket` is available for A03 native delivery handoff: body text,
  body hash, intent hash, idempotency key, target, evidence, guardrails, and safe-dispatch
  status. The explain context includes guardrails for A03/Hermes narration so numbers are
  not recalculated and the metric is not mislabeled as audited profit.
- A08 now exports an unregistered Finance API router in `backend/app/metrics/api.py`,
  tested by `backend/tests/test_a08_finance_api.py`. It exposes latest snapshot,
  snapshot detail, metric card summary, explain-context handlers, daily brief
  generate/get handlers, metric-backed daily brief generation, delivery intent ensure
  handlers, delivery-intent status reads, delivery dispatch-packet reads, and daily brief
  card-summary handlers over the read models. It is deliberately not included in
  `backend/app/main.py`; A01/A09 own central registration once auth/route contracts are
  accepted.
- A08 now exports unregistered metric read tool definitions and handlers in
  `backend/app/metrics/tools.py`, tested by `backend/tests/test_a08_metric_tools.py`.
  The exported tools are `ecom.metric.get` and `ecom.metric.explain`; both are read-only,
  versioned, structured, evidence-bearing, and not registered in the central A03 catalog.
- A08 also exports unregistered daily brief tool definitions and handlers in
  `backend/app/metrics/tools.py`, tested by
  `backend/tests/test_a08_daily_brief_tools.py`. The exported brief tools are
  `ecom.daily_brief.get`, `ecom.daily_brief.generate`, and
  `ecom.daily_brief.generate_from_metric`, `ecom.daily_brief.delivery_intent.ensure`,
  `ecom.daily_brief.delivery_intent.dispatch_packet.get`,
  `ecom.daily_brief.narration_result.record`, and
  `ecom.daily_brief.delivery_result.record`. The handlers mutate only Ecom-OS internal
  brief/intent records; they do not call Slack, Telegram, email, or any channel
  transport.
- A08 now has a degraded legacy Shopify order source bridge in
  `backend/app/metrics/legacy_sources.py`, tested by
  `backend/tests/test_a08_legacy_sources.py`. It adapts legacy `list_orders` payloads
  into the A08 `ContributionComponentSource` port as partial `net_sales` only, using
  integer minor units and order evidence refs. It intentionally leaves COGS, fee,
  shipping-cost, ad-spend, refund/chargeback, and FX inputs missing so formula coverage
  and warnings remain honest until A04 provides normalized economics inputs.
- A08 now has deterministic daily brief snapshot/fallback primitives in
  `backend/app/metrics/briefs.py`, tested by `backend/tests/test_a08_daily_briefs.py`.
  They require all default sections from the runtime spec, fill unavailable sections with
  explicit missing/unavailable coverage, compute deterministic fallback text and body
  hashes, and provide idempotent persistence helpers for brief snapshots and
  Hermes-native delivery intents. They also record narration results with deterministic
  fallback on failed/unavailable narration, and delivery results with status, evidence,
  error, trace, delivered timestamp, and attempt count. No LLM narration or channel
  transport is implemented in A08.
- A08 now has deterministic daily brief composition in
  `backend/app/metrics/brief_composer.py`, tested by
  `backend/tests/test_a08_daily_brief_composer.py`. It converts a persisted metric
  snapshot read model into the economics brief section with metric snapshot refs, trace
  refs, component refs, source evidence refs, formula version, minor-unit money, coverage,
  freshness, missing economics input warnings, and reporting window evidence. It accepts
  explicit non-economics section inputs, rejects ad-hoc economics overrides, and lets the
  brief generator fill unavailable CS/action/incident/task/research/health sections
  visibly.
- A08 now has an idempotent daily brief generation service in
  `backend/app/metrics/brief_generation.py`, tested by
  `backend/tests/test_a08_daily_brief_generation.py`. It requires exact brand, store,
  reporting date, timezone, and metric snapshot ID; rejects mismatched metric scope; then
  composes and persists the brief from the metric evidence. The unregistered Finance API
  exposes it as `POST /finance/daily-briefs/generate-from-metric`, and the unregistered
  tool catalog exposes `ecom.daily_brief.generate_from_metric`. Neither path sends a
  native channel message.
- A08 now has A03-facing daily brief delivery dispatch packets in
  `backend/app/metrics/read_models.py`, tested by
  `backend/tests/test_a08_daily_brief_delivery_packet.py`. A packet is read-only and
  includes the body A03 should deliver, the persisted idempotency key, body hash match
  status, target platform/channel, trace/evidence, and guardrails. Dispatch is allowed
  only for `pending` or `failed` intents with matching body hash; `delivered`,
  `outcome_unknown`, and body-hash mismatch states are visibly blocked.
- `backend/app/metrics/models.py` and migration
  `backend/migrations/versions/a08_001_metric_snapshots.py` now include
  `daily_briefs` and `daily_brief_delivery_intents` tables. Brief uniqueness is scoped by
  brand, store, reporting date, timezone, and revision. Delivery intent uniqueness uses
  an idempotency key for the stored brief/channel target. Delivery result callbacks are
  not idempotent; each callback increments the attempt count and records the latest
  evidence/status.
- A08 now has a local Finance UI surface at
  `frontend/src/app/(ecom)/finance/page.tsx`, detail routes at
  `frontend/src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.tsx` and
  `frontend/src/app/(ecom)/finance/daily-briefs/[briefId]/page.tsx`, plus delivery
  packet route
  `frontend/src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.tsx`.
  Shared presentation helpers live in
  `frontend/src/app/(ecom)/finance/finance-ui.tsx`, typed A08 read-model calls live in
  `frontend/src/lib/ecom-api.ts`, and coverage is in the Finance route tests. The pages
  are read-only, require exact store/snapshot/brief/intent scope instead of aggregate/
  default/latest inference, show loading/empty/unavailable/permission/error states, render
  estimated contribution margin with formula version, integer minor units, currency,
  reporting window/timezone, coverage/freshness, warnings, component evidence refs, daily
  brief fallback/narration/delivery intent status, and delivery packet safe-dispatch
  guardrails. They expect the A08 router at `/api/v1/ecom/finance` once A01/A09 mount it;
  until then the pages degrade visibly instead of substituting legacy KPI totals.
- Operator-visible behavior is summarized in
  `docs/changes/2026-06-19-a08-finance-brief.md`.
- Legacy order-derived KPIs exist in `backend/app/services/metrics.py` and are exposed by
  `GET /api/v1/ecom/metrics` in `backend/app/api/ecom.py`. They call the Shopify
  connector `list_orders` path and return revenue, order count, AOV, currency, and
  explicit unavailable reasons for session/funnel metrics.
- A board/task analytics endpoint exists in `backend/app/api/metrics.py` with schemas in
  `backend/app/schemas/metrics.py`. It powers `frontend/src/app/dashboard/page.tsx` and is
  tested by `backend/tests/test_metrics_ranges.py`,
  `backend/tests/test_metrics_kpis.py`, and `backend/tests/test_metrics_filters.py`.
- The current Ecom UI has prototype ecommerce pages at
  `frontend/src/app/(ecom)/overview/page.tsx` and
  `frontend/src/app/(ecom)/analytics/page.tsx`, with KPI rendering in
  `frontend/src/components/ecom/KpiCard.tsx` and typed calls in
  `frontend/src/lib/ecom-api.ts`.
- Store connection references are modeled in `backend/app/models/brand.py`; the current
  Shopify connector exposes read-oriented `list_orders` in
  `backend/app/services/connectors/base.py` and the direct adapter in
  `backend/app/services/connectors/shopify_direct.py`.
- Prototype insights exist in `backend/app/models/insight.py` and
  `backend/app/services/insights.py`; these are deterministic alerts but are not the v2
  daily brief input model.

### Not v2-compliant yet

- Existing displayed finance numbers still use decimal floats and live connector
  payloads. They do not store integer minor units, formula versions, component evidence,
  coverage, freshness, FX basis, attribution window, or calculation traces.
- There are no tables yet for normalized economics inputs. Metric snapshot/component and
  daily brief/delivery-intent tables exist but are not yet populated by a production
  A04/A02/A03 source implementation.
- The `/finance` route exists locally but is not linked in A06-owned global navigation,
  and the backend A08 router is still unmounted by A01/A09. The current `/analytics` page
  remains a legacy/prototype revenue dashboard and is not the Build Spec Finance surface.
- Daily brief deterministic snapshot/fallback, narration-result recording, and
  delivery-intent/result persistence primitives, metric-to-brief composition, and
  exported unregistered API/tool handlers exist, but there is no scheduler, actual A03
  Hermes narration request, native channel send implementation, or central API/tool
  registration yet.
- No A08 metric tools exist in the current MCP/tool surface. The current MCP server exposes
  legacy read/discount tools only; A03 owns the generated tool catalog path.
- No current tests prove the real A03/Hermes channel integration. Local deterministic
  fallback on narration failure, delivery-intent idempotency, delivery result visibility,
  and attempt/evidence recording are covered.

## Current architecture

At the current A08 working-tree checkpoint, finance has a tested domain formula core,
metric snapshot/component persistence, a local deterministic snapshot service,
read/explain/card models for drilldowns and Today/Finance metric/brief cards, an exported
but unregistered Finance router, exported but unregistered metric and daily brief tools, a
degraded legacy Shopify order source bridge for partial demo snapshots, deterministic
daily brief fallback/delivery-intent primitives, metric-to-brief composition, and local
read-only `/finance` summary, drilldown, and delivery-packet UI surfaces. It still has no
mounted v2 backend route, global nav registration, or registered A03 tool surface. The legacy
prototype path remains:

`frontend/(ecom)/overview|analytics` -> `frontend/src/lib/ecom-api.ts` ->
`GET /api/v1/ecom/metrics` -> `backend/app/services/metrics.py` ->
`ShopifyConnector.list_orders` -> connector payload totals.

The board metrics path is separate and should remain under the A07/A02 dashboard/task
analytics boundary unless reused through an accepted interface. Target architecture and
boundary diagram are in `DIAGRAMS.md`. The legacy source bridge is not a replacement for
the A04 economics port; it exists only to produce visibly partial, evidenced snapshots
while cross-agent contracts settle.

## Dependencies

Consumes A01 common money/time/identity, A02 trace/evidence/job/action primitives, A03
narration/channel/schedule ports, A04 commerce economics sources, A05 CS/action summary
sources, A06 UI primitives, and A07 task/research inputs. Exposes metric snapshots,
metric explanation context, and daily brief snapshots/cards to A03 and A07.
