# A01 — Platform Foundation and Identity — Workboard

## Implemented and verified (at f92adbb)

1. **Common types + typed errors** — `app/core/{ids,money,time,errors}.py`; ApiError
   handler. ✓ `test_foundation_types.py` (23).
2. **RequestContext + W3C trace propagation** — `app/core/context.py`, middleware. ✓
   `test_request_context.py` (14).
3. **Identity schema + migration** — `app/models/identity.py`,
   `a01_0001_identity_foundation.py`. ✓ real upgrade/restart/downgrade on seeded
   prototype data, `test_identity_migration.py` (3).
4. **Owner bootstrap that closes + roles + audit port + /identity** — ✓
   `test_owner_bootstrap.py` (6): anonymous denial, closure, idempotent reclaim,
   multi-user forbidden.
5. **Service & channel identity verification + enforcement fixtures** — ✓
   `test_identity_enforcement.py` (11): allowed/denied for role/service/channel.
6. **Health primitives** — `/readyz` real DB check, `/readyz/details` report. ✓
   `test_health_primitives.py` (4).
7. **Contract generation + route-registration convention** — `app/api/registry.py`;
   regenerated strict TS client. ✓ `test_contract_and_registry.py` (6).
8. **Secret redaction + detection corpus** — `app/core/redaction.py`, wired into
   logging + error boundaries. ✓ `test_secret_redaction.py` (17).

## Now (verification → ready_for_integration)

- Full-suite regression confirmation + record exact evidence in VERIFICATION.md.
- File the interface requests listed in INTERFACES.md (A02 audit sink shape, A06
  primitives, A09 contract/migration workflow, A03 `Gateway.token` redaction).

## Next (post-foundation, lower priority / cross-domain)

- Recent-auth (step-up) hook for high-risk changes (`05-OPS` §3.2) — primitive only.
- Retrofit prototype money/timestamps to v2 types behind a vertical migration (R02/R03)
  once a consuming domain (A08) needs it — avoid premature mass migration.
- Swap the no-op audit sink for A02's durable sink when available.

## Blocked

- None hard-blocking. Soft deps covered by ports/fakes (A02 audit) and the regenerated
  client (A06 will style A01-owned identity UI later).

## Exit condition

Branch `ready_for_integration` when the six acceptance items pass with recorded evidence
(VERIFICATION.md): owner-bootstrap closure ✓, server-side denial ✓, role/service/channel
fixtures ✓, no secret in logs/responses ✓, generated strict TS types used by a real
endpoint ✓, migration + restart on seeded data ✓ — pending final full-suite green.
