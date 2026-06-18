# Open Interface Requests

Only unresolved requests remain here. After acceptance and implementation, move the
canonical result into `INTERFACE-REGISTRY.md` and delete the request row.

| ID | Requester | Owner | Contract needed | Proposed shape/link | Blocking | Status |
|---|---|---|---|---|---|---|
| IR-A04-01 | A04 | A02 | Disambiguate durable **inbox/event** port from the "Durable action port". A04 needs both: (a) raw-body-verified inbox insert with unique `(source, account, source_event_id)` key + outbox; (b) action create/reuse + attempts + state machine incl. `outcome_unknown`. | See A04 `INTERFACES.md` Consumes (a04 webhook ingress + write path) | Slice 3 (webhook ingress) and Slice 6 (write path) | open |
| IR-A04-02 | A04 | A01 | Common money (minor units+ISO), time (UTC+source/collected), ID (UUIDv7 + provider-scoped external id) and typed error contracts; generated API client regeneration for new `/orders`,`/customers` schemas; central backend router registration for A04 commerce router. | `04-DATA` §3–§5 conventions | Slice 4 models + routes | open |
| IR-A04-03 | A01/A02 | A01/A02 | Trace context envelope (`trace_id`/span propagation + coverage labels verified/observed/imported/unknown) consumable by A04 sync, webhooks, and read/write tools. | Registry "Trace context envelope" | All A04 traced ops | open |
| IR-A04-04 | A04 | A06 | UI token/component contract (shadcn/Radix primitives + page/state patterns) for `/orders`,`/customers`,connection-settings, incl. stale/partial/unavailable states; navigation entries for those routes. | Registry "UI token/component contract" | Slice 5 UI | open |
| IR-A04-05 | A04 | A03 | Tool-catalog registration path for A04 read tools (`ecom.store.list/order.search/order.get/customer.get`) and write tools. **`A04→A03` edge is missing from the dependency graph** — please add and define the manifest registration contract. | Registry "Hermes bridge" / tool catalog | Slice 5 read tools, Slice 6 write tools | open |
