# A01 — Platform Foundation and Identity — Workboard

## Implemented and verified

- Nothing coded yet. Discovery complete: full normative read + backend audit at `3909904`;
  living docs reflect current truth (CURRENT/DIAGRAMS/INTERFACES/RISKS/VERIFICATION/HANDOFF).

## Now (discovery → contract_ready)

- Publish interface plan into `INTERFACE-REGISTRY.md`/`INTERFACE-REQUESTS.md` (file the 4
  requests in INTERFACES.md once coordination doc edit-rights are confirmed with A00).
- Define common types as typed ports first: `Money`, `Uuid7`, tz-aware UTC datetime, the
  typed `Error` envelope + 15-code enum, `ActorContext`/`RequestContext`/`StoreScope`.

## Next (ordered, independently verifiable slices)

1. **Common types + typed errors** → verify: unit tests for Money (no float, currency
   guard), UUIDv7 monotonic/sortable, UTC tz-aware round-trip; error envelope serializes the
   15 codes with `code/message/retryable/trace_id`. One real endpoint returns the envelope.
2. **RequestContext + trace propagation middleware** → verify: W3C `traceparent` parsed;
   `request_id`/`trace_id`/`actor`/`store_id` attached and logged structured; absent fields null.
3. **Identity schema + migrations** (`users`, `roles`, `role_permissions`, `user_roles`,
   `service_identities`, `channel_identities`) behind the existing `deps.py` seam → verify:
   migration upgrades realistic seeded prototype data; N-1 fixture passes; restart recovers.
4. **Owner bootstrap that closes** → verify: first owner created; replay anonymously →
   `forbidden`; reopen only via host recovery command; audit record emitted (to A02 fake).
5. **Server-side enforcement** for human/service/channel across HTTP (and socket where A01
   owns it) → verify: allowed/denied fixtures for role, service, channel; cross-store denial.
6. **Health primitives** (`/health` dimensions) → verify: liveness vs readiness(read/run/
   write) distinct; DB/migration/queue checks real; degraded states explicit.
7. **Contract generation hardening** + route-registration convention → verify: generated
   strict TS types used by ≥1 real endpoint; new domain router registers without ad-hoc
   `main.py` edits.
8. **Secret redaction** pass (incl. `Gateway.token`) → verify: secret-detection corpus over
   logs/traces/responses is clean.

## Blocked

- None hard-blocking. Soft dependencies handled by ports/fakes: A02 audit sink (no-op fake),
  A06 primitives (thin wrappers). Awaiting A00 confirmation on coordination-doc edit rights.

## Exit condition

Branch `ready_for_integration` only when all six acceptance items pass with evidence:
owner-bootstrap closure, server-side denial (HTTP/socket/page), identity fixtures (role +
service + channel, allowed/denied), no secret in logs/responses/traces, generated strict TS
types used by a real endpoint, and migration + restart tests pass on realistic seeded data
(handoff "Ready-for-integration acceptance" + Build Spec Slice 1).
