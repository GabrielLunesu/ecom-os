# Ecom-OS — Flow Engine (configurable CS SOPs)

The product layer that lets a non-technical merchant run their own CS: classify a
ticket → run a declarative flow → only the wording is templated.

## What shipped
- `flows` table + flow-state on tickets (flow_id/flow_step/flow_data); migration e8f9a0b1c2d3.
- `flow_engine.py`: deterministic step runner. Step types: lookup_order, cite_policy,
  send_reply, offer_discount (capped 20%, waits for the customer's decision),
  request_refund_approval (FILES an approval — never executes; Invariant 2), escalate, resolve.
  Classification = trigger-keyword match; per-step branch on the customer's reply.
- `flow_seeds.py`: two default flows — **WISMO** and **refund-deflection** (offer 10% → 20% →
  file refund for human approval).
- `FlowCSRuntime` behind the AgentRuntime interface; selected with `CS_RUNTIME=flow`.
- Ingestion **threading**: a customer reply (same conversation) appends to the open ticket and
  resumes the flow (`awaiting_customer` → `auto_handling`); replies to `needs_rep` append + notify
  and never re-auto (Invariant 3).
- API: GET /ecom/flows, PUT /ecom/flows/{id}. **Flows page**: no-code editor for triggers,
  escalate keywords, discount tiers, and per-step wording. Enable/disable per flow.

## Safety (structural, not configurable)
Discounts cap at 20% in the engine; the refund step only files into the approval lane (a human
approves; Invariant 2). Escalate keywords + unhandled cases hand to a rep; once needs_rep a flow
never resumes (Invariant 3). Customer text is untrusted data (Invariant 4).

## Verify
- 7 flow tests (incl. the full refund decline path proving it files-not-executes + discount cap +
  escalate keyword + sticky escalation) + 2 threading tests. 53 ecom tests total green.
- Live: a real "I want a refund for #1001" email → flow offered 10% off, ticket awaiting_customer,
  no refund executed.
