# A04 — Commerce Connectors and Read Models — Diagrams

## Current (audited at `3909904`)

```mermaid
flowchart LR
  subgraph Provider[External providers - untrusted]
    Shop[Shopify Admin REST 2025-01]
    Mail[Composio Outlook]
  end
  Chat[Chat UI] --> ChatSvc[/ecom/chat/]
  ChatSvc -->|live, raw dicts| DSC[DirectShopifyConnector]
  DSC --> Shop
  Metrics[metrics.py] -->|on-the-fly KPIs| DSC
  Hook[/ecom/webhooks/email\nshared-secret, NO hmac, NO inbox/] -.fire-and-forget.-> CSLoop[cs_loop poll]
  CSLoop --> Inbox[ComposioInboxConnector\nfirst-ACTIVE account]
  Inbox --> Mail
  Store[(Store row = connection ref)]
  classDef gap fill:#fee,stroke:#c00;
  class Hook,DSC gap;
```

No durable inbox, no normalized commerce store, no exact-account binding on inbox, no
durable action contract.

## Target (v2, aligned to specs)

```mermaid
flowchart TB
  subgraph Provider[External providers - untrusted, evidence not authority]
    Shop[Shopify]
    Mail[Email provider]
  end

  Shop -- raw body --> WH[Webhook ingress\nHMAC verify raw body]
  Mail -- raw body --> WH
  WH -->|verified, unique provider key| A02Inbox[(A02 durable inbox/outbox)]
  A02Inbox --> Jobs[A02 leased jobs]
  Jobs --> Sync[Sync engine\ninitial + incremental, cursors]

  subgraph A04[A04 connector layer]
    Reg[ConnectorRegistry] --> Bind[ConnectionBinding\nbrand/store/connection/account exact]
    Bind --> Exec[ProviderExecutionPort]
    Bind --> Recon[ReconciliationAdapter]
  end
  Sync --> Reg

  Sync --> Norm[(Normalized models\nstores/orders/customers/products/\nfulfilments/tracking/provider_refs\n+source/freshness/coverage/evidence)]
  Norm --> Repo[CommerceReadRepository]
  Repo --> Tools[Read tools\nstore.list/order.search/order.get/customer.get]
  Repo --> UI[/orders, /customers, connection settings\nA06 primitives, all states/]
  Norm -. normalized message events .-> A05[A05 ticket workflow]

  subgraph Write[External write = durable action]
    Exec --> Action[A02 durable action\ndigest + intent key]
    Action --> Attempt[attempts + provider op id]
    Attempt --> Recon
  end

  Conn[(connections table\nstore/inbox, health, last-good)] --> Bind
```

Trust boundary: provider payloads stay evidence; opaque provider IDs are stored separately
and never enter public contracts. Every write is a durable A02 action with exact binding;
ambiguous timeouts become `outcome_unknown` and are reconciled before any dangerous retry.
