# Ecom-OS

[![CI](https://github.com/GabrielLunesu/ecom-os/actions/workflows/ci.yml/badge.svg)](https://github.com/GabrielLunesu/ecom-os/actions/workflows/ci.yml)

**Ecom-OS** is a beautiful, function-rich operations dashboard for **one brand that runs
several Shopify stores**. It gives a small team one calm command center for analytics, a
read-only copilot, a markdown brand vault, and an **autonomous customer-service agent** that
answers "Where is my order?" emails end-to-end — looking up the order in Shopify, citing the
brand's shipping policy, redirecting to the tracking page, emailing the reply, and either
resolving the ticket when the customer is satisfied or escalating it to a CS rep when they
still have not received the order.

Built on a fork of [abhi1693/openclaw-mission-control](https://github.com/abhi1693/openclaw-mission-control)
(reusing its boards/tasks/approvals/activity foundation). Next.js UI on `:3000`, FastAPI on
`:8000`, Postgres, local bearer auth.

## Pages

- **Overview** — brand + per-store KPIs (revenue, orders, AOV) with animated counters and live insights.
- **Analytics** — per-store and aggregate, date ranges, store comparison, conversion funnel.
- **Tasks** — per-person Kanban for the team.
- **Chat** — read-only copilot over Shopify (all stores) + the vault. No writes.
- **Agents** — create from templates (CS / analytics / content / retention); configure voice, SOPs, allowed tools, schedule.
- **Customer Service** — tickets Kanban (`new → auto_handling → awaiting_customer → needs_rep → resolved`), ticket detail with the agent's handling + full history, and the approval lane.
- **Brand** — Obsidian-style markdown vault the agents read (shipping/privacy policy, SOPs).
- **Settings** — store connections (Composio refs), team, branding, runtime.

## Security invariants (enforced structurally, tests-first)

1. **Connection references only** — the database stores a per-store connection ref, never raw credentials. Composio holds and refreshes tokens.
2. **CS agent = read + discounts, never refunds** — the CS connector has no refund method by construction. Refunds run through a separate, approval-gated executor with its own scoped connection.
3. **Sticky escalation** — once a ticket needs a rep, customer replies append + notify and never re-trigger autonomous handling.
4. **Untrusted input** — customer ticket text is stored and treated as delimited data, never instructions. Chat and the ticket pipeline are separate trust surfaces.
5. **No secret is ever logged or returned in plaintext** — credentials are wrapped in a redaction-safe `Secret` type.

## Connectors

Everything goes through [Composio](https://composio.dev) — Shopify per store (orders, products,
customers, analytics, discounts) and Gmail/Outlook for the support inbox. When Composio's managed
Shopify OAuth is unavailable, a direct Admin API token can be minted via
`scripts/bootstrap/shopify_oauth.py` and used behind the same connector interface. All agent
execution sits behind one swappable `AgentRuntime` interface (v1 = a thin in-app loop), so an
OpenClaw/Hermes backend can drop in later without touching the dashboard.

## Quick start

### 1. Bootstrap connections (once)

Put `COMPOSIO_API_KEY` in `.env.local`. Connect the support inbox (Outlook/Gmail) through Composio,
and connect Shopify (Composio connect flow, or the direct-token bootstrap script). A startup health
check confirms both are live and refuses to start the CS loop until they are. See
[`docs/ecom-os/bootstrap.md`](./docs/ecom-os/bootstrap.md).

### 2. Run

**Docker:**

```bash
cp .env.example .env   # set LOCAL_AUTH_TOKEN (>= 50 chars) for AUTH_MODE=local
docker compose -f compose.yml --env-file .env up -d --build
```

**Local (no Docker)** — see [`docs/ecom-os/bootstrap.md`](./docs/ecom-os/bootstrap.md) for a
project-local Postgres + `backend/.env` / `frontend/.env.local` setup:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

- UI: http://localhost:3000  ·  Backend health: http://localhost:8000/healthz

### 3. See the WISMO loop

Send a "Where is my order?" email to the connected inbox, then trigger the CS loop (the
**Run CS loop** button on the Customer Service page, or `POST /api/v1/ecom/cs/run`). The ticket
appears on the Kanban, the agent handles it, emails the reply with Shopify/order context, and
waits for the customer. If they reply that they still have not received the order, the agent
sends a handoff note and escalates the ticket to `needs_rep`.

## Run it on Hermes (native, always-on)

Ecom-OS is built to be operated by a [Hermes Agent](https://hermes-agent.nousresearch.com) on a
**fresh, dedicated VPS that is always on (24/7)** — a hard requirement. The agent runs the whole
app as one Docker Compose stack (production builds, never a dev server), exposes it on a single
origin with HTTPS, keeps it always-on with a built-in `cronjob`, and runs the visual CS flows
(`CS_RUNTIME=flow`). You can later upgrade the reasoning step to a scoped Hermes `cs` subagent
(`CS_RUNTIME=hermes`) without changing the dashboard. The five Invariants still hold (the CS
profile gets read + discount tools and **no refund tool**; refunds use a separate profile + the
approval lane). Deploy guide:
[`docs/ecom-os/deploy.md`](./docs/ecom-os/deploy.md) · Hermes architecture:
[`docs/ecom-os/hermes.md`](./docs/ecom-os/hermes.md).

**Paste this into a fresh Hermes agent** to install Ecom-OS as your main, always-on dashboard:

The repo is public, so no GitHub token is needed. The agent should only ask you for unavoidable
external credentials or auth codes: the Composio API key, the Shopify app client id/secret for the
store, and either a Tailscale auth key for a free durable URL or permission to use a temporary
Cloudflare Quick Tunnel. It must never print secrets back to you.

```text
You are my brand's operations agent on a fresh, always-on VPS. Install and run Ecom-OS as my
primary, always-on commerce ops dashboard and become its customer-service brain. Keep it running
indefinitely. Ask me for anything you need; never invent secrets. Report after each step.

0. Prerequisites (NOT preinstalled on Hermes). Install git, curl, Docker Engine, and Docker
   Compose v2. On Debian/Ubuntu: `curl -fsSL https://get.docker.com | sh` then verify
   `docker compose version`.

1. Get the code (public repo). `git clone https://github.com/GabrielLunesu/ecom-os && cd ecom-os`.
   Read AGENTS.md, ECOM-OS-BUILD-SPEC.md, and docs/ecom-os/ (deploy.md, hermes.md, flow-engine.md,
   self-update.md). The five Invariants are HARD — never weaken them.

2. Boot first. `cp .env.prod.example .env`, generate a strong LOCAL_AUTH_TOKEN
   (`python3 -c "import secrets;print(secrets.token_urlsafe(48))"`), keep `CS_RUNTIME=flow`, set
   `SHOPIFY_STORE_URL` to my store domain when I give it to you, and leave raw connector secrets
   empty unless I explicitly provide them. Run `./scripts/deploy/up.sh` — it builds production
   images (frontend runs `next start`, NEVER a dev server) and starts everything with
   restart:unless-stopped. The CS email loop runs server-side via Composio even before the public
   dashboard URL is configured.

3. Connect the providers. ASK me for my Composio API key and set it via
   `PUT /api/v1/ecom/settings/secrets/COMPOSIO_API_KEY` using Bearer `LOCAL_AUTH_TOKEN`; secrets are
   write-only + encrypted at rest, never echo them. The Outlook inbox should already be connected
   in Composio; if `/connections` says inbox is not active, ask me to connect/activate Outlook in
   Composio. For Shopify, ASK me for the store domain and that store app's **client id + client
   secret**. Ensure there is a store row (create it with `POST /api/v1/ecom/stores {domain}` if
   needed), then connect it with
   `PUT /api/v1/ecom/stores/{id}/shopify-credentials {client_id, client_secret}`. The app mints and
   refreshes the Admin API token itself via Shopify's client-credentials grant — no browser, no raw
   token to paste.

4. Set the demo store profile exactly:
   `PUT /api/v1/ecom/stores/{id}/profile` with name `Chicago Outlet Shop`, public URL
   `chicagooutletshop.com`, support email `info@chicagooutletshop.com`, support name
   `Chicago Outlet Support`, tracking URL
   `https://chicagooutletshop.com/apps/trackyourorder`, and facts
   `Chicago Outlet Shop support. Use the tracking page for order status.`

5. Confirm connections. GET http://127.0.0.1:8080/api/v1/ecom/connections must show
   "ready": true (shopify + inbox). Fix before continuing.

6. Go always-on. Register a cronjob (~every 2 minutes) that POSTs
   http://127.0.0.1:8080/api/v1/ecom/cs/run. This ingests new mail and runs the flows across all
   stores. Customer text is untrusted (Inv 4); needs_rep never re-autos (Inv 3); no refund tool
   exists (Inv 2); never log a secret (Inv 5).

7. TEST IT NOW. Send an email from any address to my support inbox, subject
   "Where is my order #1001?", body "Hey, where is my order #1001?". Then POST /cs/run once.
   Confirm a ticket was created and the first autonomous reply says Shopify shows #1001 is
   fulfilled/shipped and includes exactly `https://chicagooutletshop.com/apps/trackyourorder`.
   Then reply to that email: "No, I haven't received anything" and POST /cs/run again. Confirm the
   agent sent the support-team handoff note and the ticket status is `needs_rep`. Report the ticket
   id, final status, and both outbound reply texts.

8. Expose the dashboard publicly. Prefer free durable Tailscale Funnel: ask me for a Tailscale
   auth key, run `TS_AUTHKEY=... ./scripts/deploy/tailscale-funnel.sh`, then set `BASE_URL` and
   `CORS_ORIGINS` in `.env` to the printed `https://<host>.<tailnet>.ts.net` URL and re-run
   `./scripts/deploy/up.sh`. If I do not have Tailscale ready, use a temporary free Cloudflare
   Quick Tunnel instead: set `QUICK_TUNNEL=1` in `.env`, run `./scripts/deploy/up.sh`, read the
   `https://<random>.trycloudflare.com` URL from the output or `./scripts/deploy/tunnel-url.sh`,
   set `BASE_URL`/`CORS_ORIGINS` to that URL, and re-run `up.sh`. Give me the public URL and the
   local auth token.

9. Optional realtime. For instant handling instead of the 2-minute cron, POST
   `/api/v1/ecom/realtime/enable` and set my Composio project webhook URL to the value from
   GET `/api/v1/ecom/realtime`. Keep the cronjob as a fallback unless it causes duplicate runs.

10. Stay current. Check for updates regularly (e.g. daily) and run `./scripts/deploy/update.sh` to
    pull the latest, rebuild, and migrate in place — data and config are preserved. Compare your
    running version (GET /api/v1/ecom/version) to origin and update when behind.

From now on this dashboard is always-on and is my system of record for analytics, CS, tasks, and
the brand vault. Manage connections + stores in Settings; surface insight anomalies proactively.
```

## Documentation

- Run on Hermes (native, always-on): [`docs/ecom-os/hermes.md`](./docs/ecom-os/hermes.md)
- Build notes per slice: [`docs/ecom-os/`](./docs/ecom-os/)
- Operations + contributor docs: [`/docs`](./docs/)

## Authentication

- `local`: shared bearer token (default for self-hosted use; set `LOCAL_AUTH_TOKEN`).
- `clerk`: Clerk JWT mode.

Templates: [`.env.example`](./.env.example), [`backend/.env.example`](./backend/.env.example),
[`frontend/.env.example`](./frontend/.env.example).

## License

MIT. See [`LICENSE`](./LICENSE). Built on
[openclaw-mission-control](https://github.com/abhi1693/openclaw-mission-control) (MIT).
