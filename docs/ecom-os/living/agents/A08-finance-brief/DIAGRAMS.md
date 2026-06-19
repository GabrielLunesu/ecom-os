# A08 — Finance, Metric Evidence, and Daily Brief — Diagrams

## Current

```mermaid
flowchart LR
  Overview["frontend/(ecom)/overview"] --> EcomApi["frontend/src/lib/ecom-api.ts"]
  Analytics["frontend/(ecom)/analytics"] --> EcomApi
  EcomApi --> EcomMetrics["GET /api/v1/ecom/metrics"]
  EcomMetrics --> LegacyMetrics["backend/app/services/metrics.py"]
  LegacyMetrics --> StoreRows["stores connection refs"]
  LegacyMetrics --> Shopify["ShopifyConnector.list_orders"]
  Shopify --> PayloadTotals["float revenue/orders/AOV from live payloads"]

  Dashboard["frontend/app/dashboard"] --> DashboardApi["GET /api/v1/metrics/dashboard"]
  DashboardApi --> TaskAnalytics["task/approval/activity analytics"]

  Shopify --> LegacyBridge["A08 degraded legacy source bridge\npartial net_sales only"]
  LegacyBridge --> LocalFormula["A08 formula/snapshot service\nmissing inputs remain warnings"]
  LocalFormula --> MetricCard["MetricCardSummary\nA07 Today + compact Finance input"]
  LocalFormula --> BriefComposer["A08 daily brief composer\nmetric evidence -> economics section"]
  BriefComposer --> BriefGeneration["A08 generation-from-metric service\nexact scope + idempotent persist"]
  BriefGeneration --> BriefPrimitives["A08 deterministic brief primitives\nfallback body + delivery intent"]
  BriefPrimitives --> BriefExports["A08 unregistered brief API/tools\nget/generate/status/ensure"]
  BriefPrimitives --> DispatchPacket["A08 dispatch packet\nbody + idempotency key + safe-dispatch gate"]
  BriefExports --> BriefCard["BriefCardSummary\nA07 Today + Finance UI input"]
  FinanceRoute["frontend/(ecom)/finance\nsummary + exact-id drilldowns"] --> EcomApi
  FinanceRoute --> FinanceRead["A08 typed finance hooks\nexpected /api/v1/ecom/finance mount\nunmounted route degrades visibly"]
  FinanceRead -.-> BriefExports
  FinanceRead -.-> LocalFormula
  DispatchPacket --> PendingHermes["A03/Hermes delivery pending\nno transport in A08"]
  PendingHermes --> ResultCallbacks["A08 result callbacks\nnarration fallback + delivery evidence"]
  ResultCallbacks --> BriefExports
```

## Target

```mermaid
flowchart TB
  Commerce["A04 commerce/economics sources\norders refunds transactions COGS ads fees shipping FX"] --> Inputs["A08 economics input normalizer\ninteger minor units + ISO currency"]
  Inputs --> Formula["Versioned formula engine\nestimated contribution margin v1"]
  Formula --> Components["metric_components\ncomponent value, source, freshness, coverage"]
  Components --> Snapshot["metric_snapshots\nwindow timezone formula version trace"]
  Snapshot --> FinanceApi["A08 Finance API + metric tools"]
  FinanceApi --> FinanceUi["/finance drilldowns\ncoverage + evidence + warnings"]
  Snapshot --> MetricCardTarget["MetricCardSummary\ncompact Today/Finance card"]
  Snapshot --> Explain["MetricExplainContext\nfor A03 narration/chat"]
  Snapshot --> BriefComposer["DailyBriefComposer\neconomics section from metric evidence"]

  Trace["A02 traces/evidence/jobs"] <--> Formula
  Trace <--> Brief["daily_briefs\nimmutable input snapshot + fallback text"]
  BriefComposer --> BriefGeneration["GenerateFromMetric\nexact snapshot scope"]
  BriefGeneration --> Brief
  CS["A05 CS/action aggregates"] --> Brief
  Tasks["A07 tasks/research/todos"] --> Brief
  Health["A09/A03/A04 health summaries"] --> Brief
  Brief --> Narration["A03 optional Hermes narration"]
  Narration --> Final["final brief text\nnumbers unchanged"]
  Brief --> Fallback["deterministic fallback\nused on narration failure"]
  Final --> Delivery["A03 Hermes-native channel/cron delivery intent"]
  Fallback --> Delivery
  Delivery --> DispatchPacket["A08 dispatch packet\nbody hash + idempotency key + guardrails"]
  DispatchPacket --> DeliveryState["idempotent delivery status/evidence/trace"]
  Brief --> Today["A07 Today brief card"]
```

Trust boundaries:

- Connector payloads and external provider records are evidence, not formula authority
  until normalized with source and freshness.
- Hermes narration can prioritize and summarize only the stored deterministic snapshot;
  it never calculates or sources numbers.
- Native channel delivery remains A03/Hermes-owned; A08 records delivery intent/status
  and idempotency.
