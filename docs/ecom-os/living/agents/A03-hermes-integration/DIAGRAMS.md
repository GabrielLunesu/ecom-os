# A03 — Hermes Native Integration and Main Chat — Diagrams

## Current (pre-v2, as audited at `3909904`)

Two disconnected gateway notions; tools hand-maintained; chat UI is a mock.

```mermaid
flowchart LR
  subgraph Browser
    EcomChat["(ecom)/chat page<br/>request/response, mock"]
    GenSess["generated gateway-session<br/>hooks (UNUSED)"]
  end
  EcomChat -->|POST /api/v1/ecom/chat| EcomAPI[ecom.py mock chat]

  subgraph Backend
    CSLoop[cs_loop._select_runtime<br/>env CS_RUNTIME]
    CSLoop --> InApp[InAppCSRuntime<br/>deterministic WISMO]
    CSLoop --> LLM[LLMCSRuntime<br/>inline TOOLS, Anthropic]
    CSLoop --> Hermes[HermesRuntime<br/>POST /delegate spike]
    MCP[mcp_server stdio<br/>7 hand-written tools]
    OC["openclaw/* (~7.1k LOC)<br/>WS JSON-RPC v3 + device pairing"]
    GW[api/gateway.py<br/>/gateways/sessions,status,commands]
  end
  Hermes -.->|HERMES_GATEWAY_URL /delegate| ExtDelegate[(hypothetical gateway)]
  LLM -->|x-api-key| Anthropic[(Anthropic)]
  GW --> OC
  OC -.->|WS| OpenClawGW[(OpenClaw gateway)]
  GenSess -.x.-> GW
```

## Target (v2 — HermesBridge as independent-peer integration)

External trust boundary at Hermes; durable truth in Ecom-OS/Postgres; honest coverage.

```mermaid
flowchart TB
  subgraph BR[Browser - no Hermes service credential]
    Chat["/chat (A03 + A06 primitives)<br/>SSE stream, tool cards, trace drawer"]
    Agents["/agents<br/>capability + conformance UI"]
  end

  subgraph ECOM[Ecom-OS backend]
    WS[Auth WS endpoint<br/>A01 identity, profile resolve]
    Bridge[["HermesBridge (A03)<br/>probe/health/session/run/stream/interrupt"]]
    BgPort[BackgroundRunPort<br/>durable job + lease]
    Catalog[[Canonical tool catalog (A03)]]
    MCPg[MCP server - generated]
    Adapter[Adapter schema - generated]
    ToolH[Ecom-OS tool handlers<br/>verified invocations]
    Cap[Capability + compatibility record]
    ChanPort[ChannelDeliveryPort / SchedulePort]
  end

  subgraph A02[A02 durable core]
    Trace[(traces / runs / spans<br/>tool-invocations / actions)]
    Ingest[idempotent trace ingest]
  end

  subgraph HERMES[Hermes Agent - independent peer]
    TUI[TUI Gateway JSON-RPC<br/>interactive sessions]
    APIsrv[API server<br/>async background runs]
    Hooks[lifecycle hooks - observer]
    Channels[native channels + cron]
    HState[(native state.db / memory<br/>NEVER written by Ecom-OS)]
  end

  Chat --> WS --> Bridge
  Agents --> Cap
  Bridge -->|interactive| TUI
  BgPort --> Bridge -->|background| APIsrv
  Catalog --> MCPg --> TUI
  Catalog --> Adapter --> TUI
  Catalog --> ToolH
  TUI -->|tool call| ToolH -->|verified| Trace
  Hooks -->|observed/unknown| Ingest --> Trace
  Bridge -->|chat_turn + run| Trace
  ChanPort --> Channels
  Cap -.probe.-> TUI
  Cap -.probe.-> APIsrv
  HState -.x.- Bridge
```

### Trust + coverage boundaries

- Hermes is an independent peer: Ecom-OS uses only supported protocols; never writes
  `state.db`/memory/profiles; never forks/patches Hermes.
- Canonical transcript stays in Hermes; Ecom-OS stores `SessionReference` + trace links.
- `verified` only for Ecom-OS-endpoint-handled invocations; hook telemetry is
  `observed`/`unknown`. Operational truth (orders/tickets/metrics) is Postgres, not Hermes.
- Browser receives only product-approved protocol methods; no service credential, no
  arbitrary protocol proxy, no sudo/secret entry via ordinary chat UI.
