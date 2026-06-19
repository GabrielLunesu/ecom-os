# Hermes ↔ Ecom-OS Compatibility Matrix

> Normative artifact required by `ECOM-OS-RUNTIME-SPEC.md` §17: the repository MUST pin
> concrete upstream versions and record behavioral deviations found by the conformance suite.
> Owner: A03. Update in the same change set as any catalog/transport/capability change.

## Pinned baseline

| Field | Value |
|---|---|
| Hermes runtime | **v0.16.0 / `v2026.6.5`** (NousResearch, TUI Gateway JSON-RPC + API server) |
| Adapter | `ecom-hermes-adapter` — not yet built (MCP path is the v1 surface) |
| MCP catalog version | `1.0.0` |
| Catalog compatibility hash | `sha256:780c7ceeb68b54794797858003bcb5d2c44b53745c498150734fb76a1d74b273` |
| Capability model | see `conformance/capabilities.json` (19 v1 flags) |

## Conformance status

**Real-Hermes conformance: BLOCKED** (risk A03-R02, interface request IR-A03-05).

No pinned Hermes v0.16.0 endpoint/credentials/install target is available in this
environment, so the seven end-to-end acceptance scenarios cannot be proven against a real
runtime. Per the owner decision on DR-A03-01, the in-repo OpenClaw gateway is a
legacy/compat transport only and MUST NOT be treated as Hermes. Conformance is therefore
gated, never faked (AGENTS I-19).

| Layer | Status | Evidence |
|---|---|---|
| Tool-catalog conformance (§15.2) | **PASS** (real Ecom-OS evidence, Hermes-independent) | `conformance.tools` in `app.hermes.conformance_cli`; `tests/test_hermes_conformance.py` |
| Interactive protocol (§15.1) | gated — fixture pass only | `tests/test_hermes_bridge.py`; real run pending IR-A03-05 |
| Background runs (§5) | gated — fixture pass only | `tests/test_hermes_runs.py` |
| Channels/cron (§15.5) | gated — fixture pass only | `tests/test_hermes_channels.py` |
| Capability negotiation / degraded behavior (§3.2) | gated — fixture pass only | `tests/test_hermes_conformance.py` |
| Release gate | **RED (exit 2, `conformance_blocked: true`)** | `uv run python -m app.hermes.conformance_cli` |

## How to run conformance

```bash
cd backend
# Fixture / blocked (default): proves the contract shape, exits 2 BLOCKED.
uv run python -m app.hermes.conformance_cli

# Local dev against the legacy OpenClaw gateway (NOT Hermes; is_real stays False):
HERMES_OPENCLAW_COMPAT_URL=ws://localhost:PORT uv run python -m app.hermes.conformance_cli

# Real Hermes (unblocks the gate). Provide a pinned v0.16.0 endpoint + token handle, then
# implement HermesNativeTransport's protocol against it:
HERMES_NATIVE_ENDPOINT=https://hermes.example HERMES_NATIVE_TOKEN_HANDLE=HERMES_TOKEN \
  uv run python -m app.hermes.conformance_cli
```

## Behavioral deviations

None recorded yet — no real runtime has been probed. Record any deviation found by the
conformance suite here, with the date and the affected capability flag(s).

## Unblock path

Provide a real Hermes v0.16.0 endpoint + credentials (IR-A03-05); the matrix and the gate
then reflect genuine results with no code change. A02 trace ingest (IR-A03-01) and A01 WS
identity (IR-A03-02) complete the verified trace links and authenticated `/chat`.
