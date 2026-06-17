# Ecom-OS — Self-update + dashboard-managed connections

## Self-update
The Hermes agent keeps the deployment current by running:

```bash
./scripts/deploy/update.sh
```

It fast-forwards the public repo, rebuilds only changed images, recreates the stack, and applies
migrations on boot. Data (the Postgres volume) and `.env` are preserved. `GET /api/v1/ecom/version`
reports the running `{version, commit}` so the agent can compare to origin and update when behind.

## Dashboard-managed connections (no terminal secrets)
Boot the stack with an empty connector config, then set everything from **Settings**:

- **API keys** (Composio, Anthropic, refund token) — `PUT /api/v1/ecom/settings/secrets/{handle}`.
  Stored **encrypted at rest** (Fernet; key derived from `SECRETS_KEY` or `LOCAL_AUTH_TOKEN`) and
  **write-only** — the API only ever returns whether a handle is set, never the value (Invariant 5).
  The connectors resolve secrets `env → Settings → encrypted store`, so env still wins if present.
- **Stores** (multi-store) — `POST /api/v1/ecom/stores {domain}` adds a store; each store gets its
  own Shopify token under handle `SHOPIFY_ACCESS_TOKEN:{domain}` (`PUT /stores/{id}/token`), so the
  CS loop runs across all stores with per-store isolation. The agent grabs fresh Shopify keys via
  the OAuth connect flow; the dashboard stores only the per-store token/ref, never in the repo.

Secrets set via the dashboard survive restarts (encrypted in Postgres) and self-updates.
