# Open Interface Requests

Only unresolved requests remain here. After acceptance and implementation, move the
canonical result into `INTERFACE-REGISTRY.md` and delete the request row.

| ID | Requester | Owner | Contract needed | Proposed shape/link | Blocking | Status |
|---|---|---|---|---|---|---|
| IR-A03-01 | A03 | A02 | Trace/run/tool-invocation envelope + idempotent ingest endpoint with coverage labels (`verified`/`observed`/`imported`/`unknown`) | Runtime Spec §6.2/§7; A03 `INTERFACES.md` "Consumes" | A03 read-tool→trace correlation, chat-turn lifecycle (Slice 0 item 4) — using local port/fake meanwhile | open |
| IR-A03-02 | A03 | A01 | Service identity + WS request context: how chat WebSocket authenticates the human and resolves the allowed Hermes profile; service-credential scoping | Runtime Spec §4.1/§14; A03 `INTERFACES.md` | `/chat` WS auth, tool context resolution — local fake identity meanwhile | open |
| IR-A03-03 | A03 | A08 | Confirm metric snapshot contract shape consumed by brief narration request | Registry row "Metric snapshot contract" (A08→A03); Runtime Spec §12.2 | Brief narration (Slice 11) — non-blocking now | open |
