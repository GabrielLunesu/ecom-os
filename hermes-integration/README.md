# hermes-integration

A03-owned conformance fixtures and the pinned compatibility contract for the Ecom-OS ↔
Hermes integration. This directory does not contain Hermes; it pins what a supported
Hermes/Ecom-OS combination MUST satisfy and is where a real Hermes is tested.

## Contents

- `COMPATIBILITY.md` — the normative compatibility matrix (Runtime Spec §17): pinned Hermes
  baseline, catalog compatibility hash, capability model, and the current conformance status
  (**real-Hermes conformance is BLOCKED** pending a pinned endpoint — IR-A03-05 / A03-R02).
- `conformance/catalog-manifest.json` — the pinned canonical tool catalog manifest
  (compatibility hash + per-tool schema hashes). A drift guard test
  (`backend/tests/test_catalog_manifest_pinned.py`) asserts the live catalog matches this
  file, so any tool/schema change is a deliberate, reviewed update (AGENTS §9).
- `conformance/capabilities.json` — the pinned v1 capability flags and per-feature
  requirements (Runtime §3.2), checked against `app.hermes.capabilities`.

## Running conformance

The runnable suite + release gate lives in the backend; see `COMPATIBILITY.md` for commands.
In short: `uv run python -m app.hermes.conformance_cli` (exits 2 BLOCKED until a real Hermes
endpoint is configured; tool-catalog conformance passes as real evidence regardless).

## Updating the pinned manifest

When tool definitions change intentionally, regenerate and review:

```bash
cd backend
uv run python -c "import json; from app.tools.generators import catalog_manifest; \
  print(json.dumps(catalog_manifest(), indent=2, sort_keys=True))" \
  > ../hermes-integration/conformance/catalog-manifest.json
```

Then update `COMPATIBILITY.md` (compatibility hash) and the adapter/MCP/generated clients in
the same change set.
