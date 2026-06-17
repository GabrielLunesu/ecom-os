# Ecom-OS — Slice 5: Vault + Brand editor

Build Spec §4 (vault), §7.7 (Brand page).

## What shipped
- `vault_documents` table (migration e2f3a4b5c6d7): markdown docs with slug/title/tags/body.
- `services/vault.py`: CRUD + keyword `search()` + seeds the **shipping** and **privacy
  policy** fixtures (with the store tracking-page URL) required by the WISMO acceptance
  test (§9a). pgvector embedding index slots in behind `search()` later.
- API: `GET /ecom/vault`, `GET /ecom/vault/{slug}`, `PUT /ecom/vault/{slug}`.
- Brand page: two-pane markdown editor (doc list, editor, live react-markdown preview)
  writing into the vault.

## Verify
- `GET /ecom/vault` returns shipping-policy + privacy-policy; shipping-policy body
  contains the tracking URL. Brand page renders + edits + saves (browser-verified).
- mypy clean; migration applies; frontend tsc 0 errors.

## Deferred
pgvector semantic index — `brew install pgvector` + `CREATE EXTENSION vector` when the
vault grows; keyword retrieval is sufficient for the WISMO SOP citation today.
