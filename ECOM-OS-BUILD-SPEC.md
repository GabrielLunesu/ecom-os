# Ecom-OS — Build Spec (for Claude Code)

A beautiful, function-rich operations dashboard for **one brand that runs several
Shopify stores**. Forked from **abhi1693/openclaw-mission-control**. This file plus
the repo's `AGENTS.md` are the source of truth. Treat **Invariants** as hard
constraints — never weaken them for looks, speed, or convenience.

---

## 0. Repo facts to respect
- `frontend/` = Next.js + TypeScript (UI on `:3000`). `backend/` = Python (API on
  `:8000`, health `/healthz`). Docker Compose via `compose.yml`. Local bearer auth
  (`LOCAL_AUTH_TOKEN`). `NEXT_PUBLIC_API_URL` resolves the API origin.
- Extend the existing `AGENTS.md` with the Invariants below; don't delete its rules.
- New pages → `frontend/`; new endpoints → `backend/`. Reuse the existing
  boards/tasks/approvals/activity models where this spec says RESHAPE.

## 1. Scope
- **Single tenant = one brand. Many Shopify stores.** A global store switcher in the
  top bar + an "All stores" aggregate view. Do NOT build org/multi-tenant switching.
- A small team of users (for the per-person task board + CS rep handoff).

## 1.5 Bootstrap & authentication — do this BEFORE the build runs
Nothing proceeds until both providers are connected.
- `.env.local` holds `COMPOSIO_API_KEY` (required). For the brand's own Shopify app you
  may also provide `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`, and the store URL per
  store — Composio uses these to run the OAuth exchange, then holds and refreshes the
  resulting token. The app never persists the raw token itself, only a connection ref.
- Operator step (once, before first run): authenticate **Shopify** and **Gmail or
  Outlook** through Composio's connect flow. The app receives a per-store connection
  reference for each (Invariant 1).
- A startup health check must confirm both connections (Shopify + inbox) are live and
  must refuse to start the CS loop until they are. Show connection status in Settings.

## 2. Invariants (write tests for these first)
1. **Composio connection references only** — never raw credentials, never a shared
   `.env`. Each store is its own Composio connected account; Settings stores the
   connection ref; Composio holds and refreshes OAuth tokens. Per-store isolation.
2. **CS agent scope = read + `write_discounts`, NEVER refunds.** The refund path is a
   separate, approval-gated executor with its own scoped connection. The CS agent has
   no refund tool at all — capability is defined by which tools exist, not by prompt.
3. **Sticky escalation** — once a ticket is `needs_rep`, customer replies append +
   notify the rep; they never re-trigger autonomous handling.
4. **Untrusted input** — customer ticket text is delimited data, never instructions.
   The Chat copilot and the ticket pipeline are separate trust surfaces.
5. **No secret is ever logged or returned in plaintext.**

## 3. Design system — beautiful, RICH in function, minimal surface, native feel
Centralize every token below in one module so the whole UI is themeable from one place.
- **Components:** shadcn/ui (Radix + Tailwind) everywhere. Minimal, clean, generous
  spacing, few borders.
- **Type:** Inter, tight tracking (headings ~ -0.02 to -0.03em, body slightly tight).
  Tabular figures for all numbers/KPIs.
- **Elevation:** light, soft, low-opacity layered shadows for depth. No heavy borders,
  no hard drop shadows.
- **Motion:** Framer Motion throughout — rich animated page/route transitions, plus
  enter/exit, layout shifts, list reordering, animated KPI counters, skeleton loaders,
  and spring micro-interactions on hover/press. One shared set of duration/easing tokens.
- **Native feel:** 60fps spring physics, optimistic UI with instant feedback, zero
  layout jank, no flash of unstyled content, a ⌘K command palette, full keyboard nav,
  PWA install. Honor `prefers-reduced-motion`.
- **Rich but minimal:** progressive disclosure, command palette, and tasteful
  data-dense tables instead of clutter.

## 4. Data model (Postgres)
- `brand` (one), `stores` (many; each holds a Composio connection ref), `users`.
- `tasks` (per-person Kanban — RESHAPE existing).
- `tickets` + `messages` (direction, untrusted flag) + `evidence` + `audit`.
- `agents` (template type, config: voice, SOPs, allowed tools, schedule).
- `vault` — Obsidian-style markdown files + an **embedding index** (pgvector) for RAG.
- `insights` — output of scheduled reflection jobs (anomalies, alerts).

## 5. Connectors — everything through Composio
Shopify per store (orders, products, customers, analytics, discounts), Gmail/Outlook
for the support inbox, Klaviyo/Meta/etc. later. Scope each connection to the agent
that uses it (Invariant 1–2).

## 6. Runtime — keep it swappable
All agent execution sits behind one `AgentRuntime` interface. v1 = a thin in-app loop
(pinned model + Composio tools + cron/webhooks). Leave a clean adapter so an
OpenClaw/Hermes backend can be dropped in later without touching the dashboard.

## 7. Page / IA map (HAVE = reshape existing, BUILD = net-new)
1. **Overview** (BUILD) — brand + per-store KPIs: revenue, sessions, ATC rate,
   conversion, orders, AOV. Store filter + aggregate. Today's tasks summary.
2. **Analytics** (BUILD) — everything Shopify exposes; per-store + aggregate; date
   ranges; store-vs-store comparison; funnel.
3. **Tasks** (RESHAPE boards/tasks) — per-person Kanban assigned to team members.
4. **Chat** (BUILD) — READ-ONLY copilot over Shopify (all stores) + the vault. No writes.
5. **Agents** (BUILD) — create from TEMPLATES (CS / analytics / content / retention),
   configure voice, SOPs, allowed tools, schedule. Not open-ended agent creation.
6. **CS** (BUILD + RESHAPE approvals) — sub-pages: Overview (tickets handled this
   week/month, refunds, escalations, response time), Tickets (lanes: new →
   auto_handling → awaiting_customer → needs_rep → resolved; each links Shopify order,
   evidence, thread), Setup (per agent: SLA, tone, response prompt, handoff rules, flow).
7. **Brand** (BUILD) — markdown editor writing into the vault; agents read it.
8. **Settings** (BUILD) — store connections (Composio refs), team/users, branding,
   runtime selection.

## 8. Build order (one PR per slice; ship + verify before the next)
1. Design system: shadcn + Inter-tight + shadow/motion tokens + app shell, store
   switcher, ⌘K palette, page-transition layout.
2. Auth + brand/stores/users + Settings store-connection model (Composio refs) +
   Shopify and Gmail/Outlook connect flow + startup health check that both are live. **Tests.**
3. Shopify read via Composio → Overview + Analytics (per-store + aggregate).
4. Tasks board (reshape).
5. Vault + embedding index + Brand page editor.
6. Chat (read-only) over Shopify + vault.
7. Ticket store + ingestion (Gmail/Outlook via Composio + Shopify webhooks). **Tests.**
8. CS pages (Overview / Tickets / Setup) + sticky escalation. **Tests.**
9. Agents page (templates + config) behind the AgentRuntime interface.
10. CS agent loop (Tier 0/1 with discount caps) + `escalate` → approval lane.
11. Refund executor (separate scoped connection, approval-gated). **Tests.**
12. Insights/reflection jobs (delivery-window anomaly, refund-risk per SKU, ticket-spike).

## 9. Definition of done

### 9a. End-to-end acceptance test (the build is done when this passes live)
Fixtures: one example **WISMO SOP** on the CS agent, and brand-vault files for the
**shipping policy** and **privacy policy**, plus the store's **tracking-page URL**.
With Shopify + the inbox connected via Composio, this full loop must run with no human
touch:
1. A real "Where is my order?" email lands in the connected support inbox.
2. Ingestion creates a ticket in the CS Tickets Kanban (`new` → `auto_handling`).
3. The CS agent applies the WISMO SOP: looks up the order in Shopify, references the
   shipping/privacy policy from the vault, and redirects the customer to the tracking
   page where they can find their status.
4. The agent autonomously **sends the reply** to the customer via Gmail/Outlook.
5. Opening the ticket shows how it was handled and the full message history (the
   inbound email + the agent's outbound reply).
6. Because the email was answered, the ticket auto-closes (`resolved`).

### 9b. Per slice
Lint/CI green; endpoints authed; no secret logged or returned; Invariants 1–5 hold;
the surface uses the shadcn + native-feel design system; a short `docs/` note added.
