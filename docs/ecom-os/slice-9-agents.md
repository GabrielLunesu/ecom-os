# Ecom-OS — Slice 9: Agents (templates + config)

Build Spec §7.5. Templates + config only, behind the AgentRuntime interface.

## What shipped
- `agent_configs` table (migration b5c6d7e8f9a0): template, name, voice, SOPs,
  allowed_tools, schedule, enabled.
- Fixed templates (CS / analytics / content / retention) + a seeded CS agent config
  (WISMO SOP, read+discount tools, webhook schedule).
- API: GET /ecom/agents/templates, GET /ecom/agents, PUT /ecom/agents/{id}.
- Agents page: template gallery + CS config editor (voice/SOPs/schedule/enable toggle).
  The editor surfaces the Invariant-2 guarantee: capability is bound by the connector
  layer (read + discounts), no refund tool to grant.
- Removed the legacy Mission Control /agents route (superseded by the Ecom-OS page).

## Verify
- Browser: 4 template cards render; CS editor shows voice/SOPs/tools + the Invariant-2
  callout. mypy clean; next build green.
