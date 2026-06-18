# Deploy Ecom-OS (production, always-on)

**Hard requirement:** Ecom-OS runs on a **fresh, dedicated VPS that is always on (24/7)**,
operated by the Hermes agent. The whole app runs as one Docker Compose stack on that box —
**production builds only, never a dev server** — exposed through a single origin with a real
HTTPS hostname via Cloudflare Tunnel (no inbound ports opened).

```
VPS (Hermes, 24/7)
 └ docker compose -f compose.yml -f compose.prod.yml up -d --build
      db + redis + backend + frontend (next start) + webhook-worker
      + proxy (Caddy):  / → frontend,  /api · /healthz → backend     (single origin, no CORS)
 └ cloudflared  →  https://app.<yourdomain>   (auto-TLS at the edge, no open ports)
```

Why this shape: one box the agent fully controls, restart-on-failure for durability, a single
origin (kills CORS/token-leak bugs), and a tunnel so the VPS needs **no inbound ports** — just
outbound from `cloudflared`.

## Steps

1. **Provision** a small always-on VPS; install Docker Engine + Compose v2.
2. **Configure**: `cp .env.prod.example .env` and fill it in (strong `LOCAL_AUTH_TOKEN`,
   `COMPOSIO_API_KEY`, `SHOPIFY_STORE_URL`, the inbox + Shopify connections, and `CS_RUNTIME`).
3. **Tunnel** (recommended): in the Cloudflare dashboard create a Tunnel, route your public
   hostname → `http://proxy:80`, and paste the token into `TUNNEL_TOKEN`. Set `BASE_URL` and
   `CORS_ORIGINS` to that hostname.
4. **Launch**:
   ```bash
   ./scripts/deploy/up.sh
   ```
   It preflights the config, builds + starts the stack (adds `--profile tunnel` when
   `TUNNEL_TOKEN` is set), and waits for `/healthz`. Stop with `./scripts/deploy/down.sh`.
5. **Verify**: open the hostname; `GET /api/v1/ecom/connections` (authed) should report Shopify +
   inbox live ("CS loop ready"). Send a WISMO test email and run the CS loop.

## The CS brain on this box

Set `CS_RUNTIME=hermes` (or `llm`) in `.env`. The Hermes agent points its scoped `cs` profile at
the bundled MCP server (`python -m app.mcp_server`, read + discount tools only — no refund tool)
and registers a `cronjob` to run the loop continuously. See
[`docs/ecom-os/hermes.md`](./hermes.md).

## Expose it for free (no domain)

Don't want to buy a domain? Run a **Cloudflare Quick Tunnel** — free, no account, no token,
HTTPS included, and the agent can do it itself:

```bash
QUICK_TUNNEL=1 ./scripts/deploy/up.sh      # prints a https://<random>.trycloudflare.com URL
./scripts/deploy/tunnel-url.sh               # re-print the current URL
```

Open that URL and log in with `LOCAL_AUTH_TOKEN`. The URL changes if the tunnel restarts
(fine for a dashboard). For a **stable** hostname later, buy a cheap domain and use the
named tunnel (`TUNNEL_TOKEN`). A purely private option: `ssh -L 8080:127.0.0.1:8080 <user>@<vps>`
then open http://localhost:8080. **Realtime** needs a public URL — set `BASE_URL` to the
tunnel URL, re-run `up.sh`, then enable it in Settings -> Realtime.

## Optional: Vercel frontend

If you want a CDN/custom-domain marketing-grade frontend, you can instead deploy `frontend/` to a
Vercel account (`vercel deploy --prod`) and point `NEXT_PUBLIC_API_URL` at the backend's tunnel
hostname (this re-introduces CORS — set `CORS_ORIGINS` to the Vercel origin). The all-in-one VPS
path above is the blessed default; Vercel is opt-in.

## Notes / limits

- The frontend image runs `next start` (a production build), not `next dev`.
- `compose.prod.yml` does not publish backend/frontend to the host; the proxy is the only entry,
  bound to loopback and reached publicly only through `cloudflared`.
- All services use `restart: unless-stopped`. Pair with the Hermes agent's health check for
  recovery beyond container restarts.
