# Ecom-OS — Slice 7: Ticket store + Outlook ingestion

Build Spec §4, §7.6, Invariants 3 & 4 (tests-first).

## What shipped
- Ticket model: `tickets` + `ticket_messages` (direction, **untrusted** flag) +
  `ticket_evidence` + `ticket_audit` (migration f3a4b5c6d7e8).
- `ComposioInboxConnector` fully implemented over Composio's tool-execute API
  (OUTLOOK_OUTLOOK_LIST_MESSAGES / REPLY_EMAIL / SEND_EMAIL); secrets revealed only
  into headers (Invariant 5).
- `services/tickets.py`: ingestion pulls unread mail, filters automated/marketing
  senders, dedups by message id, and stores every inbound message `untrusted=True`
  (Invariant 4). Lanes: new → auto_handling → awaiting_customer → needs_rep → resolved.
- API: `POST /ecom/tickets/ingest`, `GET /ecom/tickets`, `GET /ecom/tickets/{id}`.

## Verify
- 4 unit tests (normalize/strip-html, sender filter, untrusted flag, dedup) pass.
- Live: sent a WISMO email ("Where is my order #1001?") to info@chicagooutletshop.com,
  ran ingest → ticket created (status new), inbound message untrusted=True. Re-ingest
  adds nothing (dedup).
