# A04 — Commerce Connectors and Read Models — Current Risks and Edge Cases

Risks A04-R01..R05/R08 from the discovery audit are now mitigated in code with tests
(see `VERIFICATION.md`) and removed. Remaining open risks:

| ID | Risk/edge case | Impact | Current mitigation/test | Owner | Status |
|---|---|---|---|---|---|
| A04-R06 | A02 durable inbox/action ports are not built; A04 uses local stand-in tables (`commerce_provider_events`, `commerce_actions`) | At integration the stand-ins must be swapped for A02's canonical tables without weakening dedup/idempotency | Stand-ins implement identical uniqueness `(source,account,event_id)` and intent-key constraints; swap tracked by IR-A04-01 | A04 + A02 | open |
| A04-R07 | Live Shopify write/reconcile unverified (no live conformance fixture); managed Composio Shopify OAuth absent | Discount/refund writes can't run on live Shopify yet | Adapter declares `supports_reconciliation=False`; `composio/store` fails closed; durable write/reconcile proven via fake adapter; capability probe per I-19 before enabling | A04 | open |
| A04-R09 | Changing the connector port shape could regress `Secret` redaction / write-capability separation | Loss of I-15 / capability-by-construction guarantees | v2 ports reuse `Secret`/`ConnectionRef`; existing `test_connector_invariants.py` still green; refund executor untouched | A04 | open |
| A04-R10 | Legacy `api/ecom_webhooks.py` (shared-secret, no durable inbox) still mounted | A spoofable/duplicating ingress path coexists with the secure one | New `connectors/webhooks.py` supersedes it; retire legacy route during A05 email-ingress integration | A04 + A05 | open |
| A04-R11 | Commerce read API not yet centrally registered or auth-wrapped | Routes unusable / unauthenticated until A01/A09 mount them behind auth | Router exposed in owned package; registration + auth requested via IR-A04-02; tested via isolated app with overridden session | A04 + A01/A09 | open |

Delete resolved rows after the durable behavior/test/documentation is in place. This is
not an incident history.
