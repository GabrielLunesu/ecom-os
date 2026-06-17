# Ecom-OS — Slice 6: Chat (read-only copilot)

Build Spec §7.4. Strictly read-only; a separate trust surface from tickets (Inv 4).

## What shipped
- `services/chat.py`: deterministic read-only router — order lookup (Shopify),
  KPI summary (metrics service), and vault keyword search (whole-message then
  significant-word fallback). Never writes, never discounts, never refunds.
- API: POST /ecom/chat {message} -> {answer, sources}.
- Chat page: message thread with source-citation chips, suggestions, optimistic UI,
  spring-animated bubbles.

## Verify (live)
- "order #1001" -> "Order #1001 — total 49.95 USD, fulfillment: fulfilled, financial:
  paid." (source: shopify_order). "revenue last 30 days" -> KPI summary. "shipping
  policy" -> vault excerpt (sources: vault). Browser-verified.
