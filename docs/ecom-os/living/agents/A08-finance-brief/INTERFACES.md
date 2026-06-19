# A08 — Finance, Metric Evidence, and Daily Brief — Interfaces

## Exposes

| Interface | Version/status | Canonical schema/code | Consumers | Failure semantics |
|---|---|---|---|---|
| `MetricSnapshot` / `MetricSnapshotGet` | planned v1 | A08-owned `backend/app/metrics/` schemas/models; route/tool registration requested from A01/A03 | A03 narration/tools, A07 Today, `/finance` | Not found, inaccessible, unavailable, stale, and partial coverage are distinct; every value returns formula version, window/timezone, currency, coverage, freshness, and evidence references. |
| `MetricExplainContext` | planned v1 | A08-owned deterministic snapshot/context builder | A03 "Ask Hermes why this changed", trace tools | Returns structured components only; narration may summarize but cannot alter numbers. Missing evidence degrades coverage and emits warnings. |
| `MetricCardSummary` | exported/unregistered v1 | `backend/app/metrics/read_models.py` plus unregistered handlers in `backend/app/metrics/api.py` | A07 Today, `/finance` | Compact metric card for one exact persisted snapshot/latest scoped metric. Shows value, formula version, reporting window, coverage/freshness, missing components, warning details, trace, component count, and detail link; never substitutes legacy KPI totals. |
| `DailyBriefSnapshot` / `DailyBriefGetGenerate` | exported/unregistered v1 | A08-owned brief snapshot/fallback renderer plus `backend/app/metrics/api.py` and `backend/app/metrics/tools.py` handlers | A03 native channel/cron delivery, A07 Today brief panel | Snapshot generation is idempotent by brand/store/window/timezone/revision. Narration failure returns deterministic fallback. Delivery failure remains retryable without duplicating sent briefs. |
| `DailyBriefComposer` | local v1 | `backend/app/metrics/brief_composer.py` | A08 scheduled generation, A07/A05/A02 section input adapters | Economics comes only from persisted metric snapshot evidence. Missing operational sections are explicit unavailable/missing sections; caller-provided economics overrides are rejected. |
| `DailyBriefGenerateFromMetric` | exported/unregistered v1 | `backend/app/metrics/brief_generation.py`, `POST /finance/daily-briefs/generate-from-metric`, `ecom.daily_brief.generate_from_metric` | A03 scheduler/cron handoff, A07 Today, `/finance` | Requires exact brand/store/reporting date/timezone/metric snapshot id. Scope mismatch returns not found/invalid instead of falling back to latest/default. Creates/reuses one deterministic brief; no channel send. |
| `DailyBriefDeliveryIntent` | exported/unregistered v1 | A08-owned delivery-intent persistence plus API/tool status/ensure handlers | A03 native delivery worker, A07 Today, `/finance` | Ensuring an intent is idempotent by brief/platform/channel and leaves status `pending`; A08 does not perform the channel send. |
| `DailyBriefDeliveryPacket` | exported/unregistered v1 | `backend/app/metrics/read_models.py`, `GET /finance/daily-brief-delivery-intents/{intent_id}/dispatch-packet`, `ecom.daily_brief.delivery_intent.dispatch_packet.get` | A03 native delivery worker | Read-only dispatch handoff with body text, body hash, idempotency key, target, evidence, trace, and guardrails. Dispatch is allowed only for `pending`/`failed` intents with matching body hash; `outcome_unknown`, `delivered`, and body mismatch block dispatch. |
| `DailyBriefNarrationResult` / `DailyBriefDeliveryResult` | exported/unregistered v1 | A08-owned result-recording helpers plus API/tool handlers | A03 Hermes narration/native delivery callbacks, A07 Today, `/finance` | Failed/unavailable narration keeps deterministic fallback as final text. Delivery callbacks record attempt count, status, evidence, trace, error, and delivered timestamp; callbacks do not send messages. |
| `BriefCardSummary` | exported/unregistered v1 | `backend/app/metrics/read_models.py` plus unregistered card handlers in `backend/app/metrics/api.py` | A07 Today, `/finance` | Shows status, reporting window, coverage/freshness, narration status, trace, delivery state/counts, warnings, metric refs, and detail link; never hides stale or failed generation. |
| `/finance` UI routes | local/unregistered nav | `frontend/src/app/(ecom)/finance/page.tsx`, `frontend/src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.tsx`, `frontend/src/app/(ecom)/finance/daily-briefs/[briefId]/page.tsx`, `frontend/src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.tsx`; typed calls in `frontend/src/lib/ecom-api.ts` | Operators, A06/A09 route integration | Requires exact store/snapshot/brief/intent scope; legacy KPI totals and latest/default records are not substituted. Missing mount, 404, permission, stale, partial, unavailable, and error states remain visible. |

## Consumes

Accepted registry status: `docs/ecom-os/living/00-program/INTERFACE-REGISTRY.md` still
lists the A08 metric snapshot contract as `pending/proposed`, and A08's consumed A02/A03/
A04/A06/A07 contracts are not accepted/versioned yet. Until those rows are accepted, the
interfaces below are local proposals or unregistered exports only.

| Interface | Owner | Required version/status | Call sites | Fallback/degraded behavior |
|---|---|---|---|---|
| Money/time/identity/request context | A01 | pending/proposed | formula inputs, API auth, reporting windows, actor/store scope | Use local typed value objects and fixtures until accepted; no external write or privileged read without exact identity/store scope. |
| Trace/evidence/job/action primitives | A02 | pending/proposed | calculation traces, evidence links, scheduled generation jobs, delivery/action status | Build local ports/fakes; mark trace coverage unavailable until A02 contract exists. No unsupported delivery side effect is claimed verified. |
| Hermes narration, channel delivery, cron/schedule | A03 | pending/proposed | optional brief narration, native delivery intent/status, explain-change prompt context | Deterministic fallback remains canonical; if Hermes/channel unavailable, generation succeeds and delivery is pending/degraded. |
| Commerce economics sources | A04 | pending/proposed | orders, refunds, transactions, COGS, fees, shipping, ad spend, FX/source freshness | Local fixtures and adapters above legacy `list_orders`; missing or stale components reduce coverage and create warnings, never zero-filled silently. |
| CS/action/task/research aggregates | A05/A07 | pending/proposed | daily brief sections and Today cards | Omit unavailable sections with explicit partial coverage; deterministic metrics still generate. |
| UI primitives/state patterns | A06 | pending/proposed | `/finance`, drilldowns, brief cards | Use existing ecom components only as migration input; request final primitives/nav registration from A06/A09. |

## Open requests

Cross-domain requests are kept here until the owning agent accepts/version-registers the
contract. A08 does not edit A00-owned programme files.

Current A08-local requests:

1. A04 -> A08: normalized economics source port for orders, refunds, transactions, COGS,
   ad spend, fees, shipping/fulfilment cost, and FX rates with source timestamps,
   collected timestamps, exact store/connection scope, provider IDs, and freshness.
2. A02 -> A08: trace/evidence/job interfaces for calculation runs, metric component
   evidence links, daily-brief job idempotency, and delivery status recording.
3. A03 -> A08: narration and native channel delivery ports with capability flags,
   idempotency key semantics, delivery evidence, and failure/retry status.
4. A07 -> A08: task/research/today attention input contract plus `MetricCardSummary`
   and `BriefCardSummary` consumer contracts.
5. A06/A09/A01 -> A08: `/finance` nav registration and backend router mount for
   `/api/v1/ecom/finance`; local route content now exists and stays unlinked until
   accepted.

Current exported but unregistered code:

- API router: `backend/app/metrics/api.py`
- Read/explain models: `backend/app/metrics/read_models.py`
- Snapshot service/source port: `backend/app/metrics/snapshots.py`
- Degraded legacy Shopify order source bridge: `backend/app/metrics/legacy_sources.py`
- Daily brief composer: `backend/app/metrics/brief_composer.py`
- Daily brief generation service: `backend/app/metrics/brief_generation.py`
- Daily brief snapshot/fallback and delivery intent helpers: `backend/app/metrics/briefs.py`
- Local Finance UI routes: `frontend/src/app/(ecom)/finance/page.tsx`,
  `frontend/src/app/(ecom)/finance/metric-snapshots/[snapshotId]/page.tsx`, and
  `frontend/src/app/(ecom)/finance/daily-briefs/[briefId]/page.tsx`, and
  `frontend/src/app/(ecom)/finance/daily-brief-delivery-intents/[intentId]/page.tsx`
- Shared Finance UI helpers: `frontend/src/app/(ecom)/finance/finance-ui.tsx`
- Frontend typed A08 finance calls: `frontend/src/lib/ecom-api.ts`
- Tool definitions/handlers for A03 registration: `backend/app/metrics/tools.py`
