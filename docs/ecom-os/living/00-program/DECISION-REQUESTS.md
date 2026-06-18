# Open Decision Requests

Use this only when work cannot be resolved by an existing invariant, ADR, spec, or owned
interface. A00 records the conflict; the product owner accepts/rejects; the relevant owner
writes an ADR if the decision is architectural.

| ID | Raised by | Decision needed | Options and consequences | Work that can continue | Owner decision |
|---|---|---|---|---|---|
| DR-A03-01 | A03 | Is the existing `backend/app/services/openclaw/**` gateway (WS JSON-RPC v3 + device pairing, DB `openclaw_agency`) the same product as the spec-pinned Hermes (`v0.16.0`/`v2026.6.5`, NousResearch TUI Gateway JSON-RPC + API server), or a separate predecessor to retire? | (a) Same product/renamed → reuse OpenClaw transport core, map methods to Hermes v2 contract; large code reuse. (b) Separate → build `HermesBridge` fresh against documented Hermes contract, keep OpenClaw only as pattern reference; correct per Runtime Spec §17 but more new code. Wrong assumption either rebuilds working code or wrongly couples to a non-Hermes protocol. | Build `HermesBridge` behind typed ports + fakes + conformance fixtures against the documented Hermes contract; treat OpenClaw as reference only until decided (Operating Protocol §7). | pending |
