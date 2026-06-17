# Ecom-OS

[![CI](https://github.com/GabrielLunesu/ecom-os/actions/workflows/ci.yml/badge.svg)](https://github.com/GabrielLunesu/ecom-os/actions/workflows/ci.yml)

**Ecom-OS** is a beautiful, function-rich operations dashboard for **one brand that runs
several Shopify stores**. It gives a small team one calm command center for analytics, a
read-only copilot, a markdown brand vault, and an **autonomous customer-service agent** that
answers "Where is my order?" emails end-to-end — looking up the order in Shopify, citing the
brand's shipping policy, redirecting to the tracking page, emailing the reply, and closing the
ticket, with no human in the loop.

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
appears on the Kanban, the agent handles it, emails the reply, and the ticket auto-closes.

## Documentation

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
