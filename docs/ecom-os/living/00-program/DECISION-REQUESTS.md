# Open Decision Requests

Use this only when work cannot be resolved by an existing invariant, ADR, spec, or owned
interface. A00 records the conflict; the product owner accepts/rejects; the relevant owner
writes an ADR if the decision is architectural.

| ID | Raised by | Decision needed | Options and consequences | Work that can continue | Owner decision |
|---|---|---|---|---|---|
| DR-A03-01 | A03 | Is the existing `backend/app/services/openclaw/**` gateway (WS JSON-RPC v3 + device pairing, DB `openclaw_agency`) the same product as the spec-pinned Hermes (`v0.16.0`/`v2026.6.5`, NousResearch TUI Gateway JSON-RPC + API server), or a separate predecessor to retire? | (a) Same product/renamed → reuse OpenClaw transport core. (b) Separate → build `HermesBridge` fresh; OpenClaw is compat/dev only. | `HermesBridge` built behind typed ports/fakes; `HermesNativeTransport` is the real-Hermes boundary; `OpenClawCompatTransport` is dev-only. Real-Hermes conformance stays BLOCKED. | **Owner decision (user): NOT the same product.** Treat OpenClaw as a legacy compatibility transport only. Add `HermesNativeTransport` stub for a real pinned Hermes (endpoint/credentials/install TBD). Real-Hermes conformance is **BLOCKED**, not complete, until tested against actual Hermes. Decision recorded; A03-R02 tracks the remaining block. |
