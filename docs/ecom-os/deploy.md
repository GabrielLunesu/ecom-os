# Deploy Ecom-OS (production, always-on)

**Hard requirement:** Ecom-OS runs on a **fresh, dedicated VPS that is always on (24/7)**,
operated by the Hermes agent. The whole app runs as one Docker Compose stack on that box —
**production builds only, never a dev server** — exposed through a single origin with HTTPS
through Tailscale Funnel, Cloudflare Quick Tunnel, or a named Cloudflare Tunnel.

```
VPS (Hermes, 24/7)
 └ docker compose -f compose.yml -f compose.prod.yml up -d --build
      db + redis + backend + frontend (next start) + webhook-worker
      + proxy (Caddy):  / → frontend,  /api · /healthz → backend     (single origin, no CORS)
 └ public HTTPS →  Tailscale Funnel (durable, free) or cloudflared (quick/named tunnel)
```

Why this shape: one box the agent fully controls, restart-on-failure for durability, a single
origin (kills CORS/token-leak bugs), and a tunnel/funnel so the VPS does not need public inbound
ports.

## Steps

1. **Provision** a small always-on VPS; install Docker Engine + Compose v2.
2. **Configure**: `cp .env.prod.example .env`, generate a strong `LOCAL_AUTH_TOKEN`, keep
   `CS_RUNTIME=flow`, and set connector secrets through the Settings API after boot.
3. **Public URL**: for a free durable URL, use Tailscale Funnel; for a zero-account temporary URL,
   use `QUICK_TUNNEL=1`; for your own domain, use a named Cloudflare Tunnel.
4. **Launch**:
   ```bash
   ./scripts/deploy/up.sh
   ```
   It preflights the config, builds + starts the stack (adds `--profile tunnel` when
   `TUNNEL_TOKEN` is set), and waits for `/healthz`. Stop with `./scripts/deploy/down.sh`.
5. **Verify**: open the hostname; `GET /api/v1/ecom/connections` (authed) should report Shopify +
   inbox live ("CS loop ready"). Send a WISMO test email and run the CS loop twice: first to answer
   with Shopify context, then after a "No, I haven't received anything" reply to escalate to
   `needs_rep`.

## The CS brain on this box

Use `CS_RUNTIME=flow` for the production demo: the visual flow engine owns routing, Shopify
context, discount/refund guardrails, and human handoff. Later, set `CS_RUNTIME=hermes` (or `llm`)
only when you want the full model-driven runtime. The Hermes agent can point its scoped `cs`
profile at the bundled MCP server (`python -m app.mcp_server`, read + discount tools only — no
refund tool). See [`docs/ecom-os/hermes.md`](./hermes.md).

## Durable public URL (recommended): cheap domain + Cloudflare named tunnel

A stable link that never changes (like `app.yourbrand.com`), clean HTTPS, no interstitial,
no open ports. ~$1-10/yr for the domain; everything else is free. The named-tunnel service is
already wired in `compose.prod.yml`.

One-time setup (≈10 min):
1. Buy a domain (Cloudflare Registrar / Namecheap / etc.).
2. Add it to **Cloudflare** (free plan) and switch its nameservers to Cloudflare.
3. **Cloudflare Zero Trust → Networks → Tunnels → Create a tunnel** → connector "Cloudflared".
   Copy the **tunnel token** it shows.
4. In that tunnel → **Public Hostname** → add: hostname `app.yourdomain.com`,
   Service = **HTTP**, URL = `proxy:80`. (cloudflared reaches the `proxy` service on the
   compose network.)
5. In `.env` set:
   ```
   TUNNEL_TOKEN=<the tunnel token>
   BASE_URL=https://app.yourdomain.com
   CORS_ORIGINS=https://app.yourdomain.com
   ```
6. `./scripts/deploy/up.sh` — it runs with the tunnel. Open `https://app.yourdomain.com`, log in
   with `LOCAL_AUTH_TOKEN`. The URL is permanent across restarts/updates.

This stable URL is also what **realtime** uses: after step 6, `POST /api/v1/ecom/realtime/enable`
and set your Composio project webhook URL from `GET /api/v1/ecom/realtime`.

## Completely free + durable: Tailscale Funnel

No domain, no cost, a **permanent** URL, clean HTTPS, no interstitial. The only requirement is
a free Tailscale account. You get `https://<host>.<tailnet>.ts.net` that never changes.

One-time (free Tailscale account, https://login.tailscale.com/admin):
1. Settings -> Features: enable **HTTPS Certificates** and **Funnel**.
2. Settings -> Keys: generate an **auth key**.
3. On the VPS (stack already running): `TS_AUTHKEY=tskey-... ./scripts/deploy/tailscale-funnel.sh`
   — it installs Tailscale, joins the tailnet, funnels the dashboard, and prints the URL.

Set `BASE_URL`/`CORS_ORIGINS` to that URL and re-run `up.sh` to also enable realtime.

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
