# Open Interface Requests

Only unresolved requests remain here. After acceptance and implementation, move the
canonical result into `INTERFACE-REGISTRY.md` and delete the request row.

| ID | Requester | Owner | Contract needed | Proposed shape/link | Blocking | Status |
|---|---|---|---|---|---|---|
| IR-A03-01 | A03 | A02 | Trace/run/tool-invocation envelope + idempotent ingest endpoint with coverage labels (`verified`/`observed`/`imported`/`unknown`) | Runtime Spec §6.2/§7; A03 `INTERFACES.md` "Consumes" | A03 read-tool→trace correlation, chat-turn lifecycle (Slice 0 item 4) — using local port/fake meanwhile | open |
| IR-A03-02 | A03 | A01 | Service identity + WS request context: how chat WebSocket authenticates the human and resolves the allowed Hermes profile; service-credential scoping | Runtime Spec §4.1/§14; A03 `INTERFACES.md` | `/chat` WS auth, tool context resolution — local fake identity meanwhile | open |
| IR-A03-03 | A03 | A08 | Confirm metric snapshot contract shape consumed by brief narration request | Registry row "Metric snapshot contract" (A08→A03); Runtime Spec §12.2 | Brief narration (Slice 11) — non-blocking now | open |
| IR-A03-04 | A03 | A09 | Register a read-only `/system` route exposing `hermes_health_snapshot` (compatibility record + conformance + per-feature readiness, with `conformance_blocked`) | `backend/app/hermes/health.py`; Build Spec Slice 3 capability UI | System-health visibility of Hermes capability/blocked state — A03 supplies the service fn | open |
| IR-A03-05 | A03 | infra/human | Provide a pinned **real Hermes v0.16.0** endpoint + credentials (or install target) to unblock real conformance + the seven acceptance scenarios | DR-A03-01 owner decision; `HermesNativeTransport` seam; A03-R02 | Real-Hermes transport, conformance evidence, `ready` state — all currently BLOCKED | open |
| IR-A03-06 | A03 | A01/A09 | Register `app/api/hermes_chat.py` `router` (prefix `/hermes`) in `app/main.py`; confirm `get_chat_identity` → A01 identity→profile mapping replaces the placeholder | `backend/app/api/hermes_chat.py`; A03 `INTERFACES.md` | `/chat` backend + `/hermes/health` reachable; identity binding (IR-A03-02) | open |
