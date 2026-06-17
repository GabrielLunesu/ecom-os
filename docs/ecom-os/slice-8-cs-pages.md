# Ecom-OS — Slice 8: CS pages (board + detail)

Build Spec §7.6. Surfaces the ticket lifecycle and the agent's handling.

## What shipped
- CS page with tabs: **Tickets** (Kanban: new → auto_handling → awaiting_customer →
  needs_rep → resolved), **Overview** (open / auto-resolved / needs-rep counts), **Setup**
  (CS agent capability + invariants).
- A **Run CS loop** button (POST /ecom/cs/run) — ingest + handle from the UI.
- Ticket detail drawer: status, a "How it was handled" evidence trail (order lookup,
  policy cite, tracking), and the full message history (inbound customer marked
  untrusted, outbound agent reply). Spring-animated drawer + lane cards.
- Backend: ticket detail now includes evidence (`ticket_evidence` query helper).

## Verify (browser, live)
- Board renders all five lanes; the WISMO ticket sits in **Resolved**.
- Opening it shows evidence (order #1001 → shipping-policy → tracking URL) and the
  agent's reply. Confirms §9a steps 5-6 visually.
