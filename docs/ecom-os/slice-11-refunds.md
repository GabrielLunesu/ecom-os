# Ecom-OS — Slice 11: Refund executor (approval-gated, Invariant 2)

Build Spec §8.11. Refunds are a separate path the CS agent cannot reach.

## What shipped
- `refund_requests` table (migration a4b5c6d7e8f9): pending → approved/rejected →
  executed/failed.
- `RefundExecutor` (own scoped connection via `SHOPIFY_REFUND_ACCESS_TOKEN`) now
  performs the real Shopify refund (find capture txn → create refund). It refuses
  without an approval (RefundNotApprovedError) and without its own token
  (SecretResolutionError) — never falls back to the CS connection.
- `services/refunds.py`: request / list / approve(+execute) / reject. The CS agent and
  InAppCSRuntime have no import path into this module.
- API: GET/POST /ecom/refunds, POST /ecom/refunds/{id}/approve|reject.

## Verify
- 5 tests: executor requires approval; real executor needs its own scoped token;
  request pending→executed on approve; failure recorded (not silent); reject never
  executes. Plus the connector-invariant tests prove the CS connector has no refund
  method. All green.

## Operator note
To enable live refunds, provision a SECOND Shopify app scoped to `write_orders` and
set its token as `SHOPIFY_REFUND_ACCESS_TOKEN`. The CS app stays read + discounts.
