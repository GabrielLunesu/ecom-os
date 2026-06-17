# Ecom-OS — Bootstrap & connections

Per Build Spec §1.5, nothing in the CS loop runs until Shopify **and** the support
inbox are connected. This note records how the brand's connections are wired.

## Outlook (support inbox) — Composio
Connected through Composio (managed OAuth). Connected account `ca_gEiVljgoyAoz`,
mailbox `info@chicagooutletshop.com`, scopes include `Mail.Read` / `Mail.ReadWrite` /
`Mail.Send`. `COMPOSIO_API_KEY` lives in `.env.local`.

## Shopify — direct Admin API token (Composio OAuth unavailable)
Composio's managed Shopify OAuth was not working, so we mint the brand's own
**offline Admin API access token** via the Authorization Code grant and store it as
`SHOPIFY_ACCESS_TOKEN` in `.env.local` (never logged, never committed — Invariant 5).

```
python3 scripts/bootstrap/shopify_oauth.py
```

The script starts a local loopback listener on `:53682`, opens Shopify's consent
screen, validates the HMAC + `state`, exchanges the code, and writes the token. The
redirect `http://localhost:53682/callback` must be in the app's Allowed redirection
URL(s). Store = **CHICAGO OUTLET** (`stv0xe-c4.myshopify.com`).

### Scope / Invariant 2 caveat
Shopify's managed install granted the **app's configured scopes**, which are broad and
include `write_orders`. The requested read-first set was narrower. We therefore enforce
Invariant 2 **in code**: the CS agent connector exposes only read + discount tools, and
refunds are a separate approval-gated executor — "capability is defined by which tools
exist, not by prompt." Production hardening: split into two Shopify apps (CS read +
`write_discounts` vs. a refund app with `write_orders`).

### Analytics caveat
The token lacks `read_reports`/`read_analytics`, so ShopifyQL session/conversion/ATC
metrics are unavailable. Revenue/orders/AOV derive from the Orders API; session-based
metrics degrade gracefully and are labeled as unavailable.
