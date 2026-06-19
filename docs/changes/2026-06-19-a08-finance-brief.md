# A08 Finance Metrics and Daily Brief

## Operator-visible behavior

- Adds the local `/finance` surface for deterministic estimated contribution margin, metric
  evidence, daily brief status, and delivery packet drilldowns. The route remains unlinked
  until A06/A09 accept navigation registration.
- Finance reads require exact store, snapshot, brief, or delivery-intent scope. The UI does
  not infer default/latest accounts or substitute legacy revenue/AOV metrics.
- Daily briefs now have deterministic fallback text, explicit coverage/freshness warnings,
  idempotent delivery intents, delivery result visibility, and read-only dispatch packets
  for A03 Hermes-native delivery.

## Operational notes

- Backend A08 router and tools are exported but not centrally mounted or registered yet.
- Missing COGS, ad spend, fees, shipping cost, refunds/chargebacks, FX, CS, action,
  incident, task, research, and health inputs remain visible as partial/unavailable
  coverage rather than zeroes.
- A08 records intent/status/evidence only; it does not send Slack, Telegram, email, or any
  native channel message.
