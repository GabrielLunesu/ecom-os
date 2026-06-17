# Ecom-OS — Connecting Shopify (client id + secret, no browser)

Operators only provide their Shopify app's **client id + client secret** (+ store domain) —
that's all you can get from the app. Ecom-OS obtains the Admin API token itself via Shopify's
**client-credentials grant**:

```
POST https://{shop}.myshopify.com/admin/oauth/access_token
  grant_type=client_credentials & client_id=... & client_secret=...
-> { access_token, scope, expires_in: 86399 }
```

- No browser, no OAuth redirect, no token to paste.
- The token lasts 24h; the connector caches it and refreshes before expiry.
- Per store (multi-store): creds are stored encrypted under `SHOPIFY_CLIENT_ID:{domain}` /
  `SHOPIFY_CLIENT_SECRET:{domain}` (write-only). Each store mints its own token.
- Requires an app developed by your org, installed on your own store (Shopify's precondition).
- Fallback: a static `SHOPIFY_ACCESS_TOKEN` (env or `PUT /stores/{id}/token`) still works.

Set it in the dashboard: Settings → Stores → enter Client ID + Client secret → **Connect**.
API: `PUT /api/v1/ecom/stores/{id}/shopify-credentials {client_id, client_secret}` (validates by
minting a token, marks the store connected). Verified live with the real store.
