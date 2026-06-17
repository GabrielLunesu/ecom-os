# Ecom-OS — Slice 3: Shopify read → Overview KPIs

Implements Build Spec §7.1 (Overview KPIs) via the connector layer.

## What shipped
- **Connector read**: `ShopifyConnector.list_orders(created_at_min/max)` with Shopify
  cursor pagination (Link header). Added to the interface (still no refund method).
- **Metrics service** (`services/metrics.py`): computes revenue, orders, AOV per store
  and aggregated across all stores from the Orders API. Session-based KPIs (sessions,
  conversion, ATC) are returned `null` with a reason — this connection lacks
  `read_reports`, so the UI shows "n/a" instead of wrong numbers.
- **API**: authed `GET /api/v1/ecom/metrics?store=<id|all>&days=<n>`.
- **Overview page**: live KPI cards (animated counters) scoped by the store switcher;
  store seed now uses the live Shopify shop name ("Chicago Outlet").

## Verify (browser, live)
- Overview shows Revenue $49.95, Orders 1, AOV $49.95 from Shopify; Sessions/Conversion/
  ATC show "n/a". Sidebar, store switcher, ⌘K palette all work; no console errors.
- Settings shows Shopify "connected: CHICAGO OUTLET", Inbox "outlook: ACTIVE",
  "CS loop ready", store "Connected".

## Fix of note
`customFetch` wraps responses as `{data,status,headers}`; the ecom hooks now unwrap
`.data` (the initial version passed the wrapper to `.map`, crashing the shell).

## Known dev warning (pre-existing, not introduced here)
`src/components/ui/global-loader.tsx` emits a recoverable hydration warning
(`data-cy` mismatch) visible as Next's dev "1 Issue" badge. It is pre-existing in the
fork and does not affect production.
