# Ecom-OS — Slice 12: Insights / reflection jobs

Build Spec §4, §8.12. Anomalies + alerts computed from live data.

## What shipped
- `insights` table (migration d7e8f9a0b1c2).
- `services/insights.generate_insights`: deterministic reflection job computing
  delivery-window anomaly (unfulfilled orders > 7 days), refund-risk (pending/failed
  refunds), and ticket-spike + CS health (tickets this week / auto-resolved / needs-rep).
  Regenerated on demand; schedulable via the runtime/cron.
- API: GET /ecom/insights. Surfaced as an Insights section on Overview with severity
  icons.
- `list_orders` now returns `fulfillment_status` for the delivery-window check.

## Verify (live)
- GET /ecom/insights -> Fulfillment on track / No refund backlog / 1 ticket this week
  (1 auto-resolved). Rendered on Overview. mypy clean; tsc 0 errors.
