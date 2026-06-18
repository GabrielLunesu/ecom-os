# Owner bootstrap and identity foundation (A01)

**Date:** 2026-06-19 · **Owner:** A01 (platform foundation)

## Operator-visible behaviour

- A freshly installed instance starts with **owner bootstrap open**. The first
  authenticated user can claim ownership via `POST /api/v1/identity/owner-bootstrap`,
  which grants the `owner` role and **closes bootstrap**.
- Once closed, the claim is rejected for anyone but the established owner with a typed
  `forbidden` error. An anonymous (unauthenticated) request can never claim ownership —
  all `/api/v1/identity/*` routes require authentication server-side.
- Re-opening bootstrap is a **host-only recovery** operation (`reopen_bootstrap`),
  intentionally not reachable from the browser/API.
- `GET /api/v1/identity/me` returns the caller's effective roles and permissions.
- `GET /api/v1/identity/bootstrap-status` reports whether bootstrap is open and whether
  the caller is the owner.

## Notes

- Instance roles (`owner`, `admin`, `operator`, `cs_lead`, `cs_rep`, `finance`,
  `viewer`) and a foundation permission set are seeded idempotently on first claim.
- Identity/config changes emit audit events through the A02 audit-sink port. Until A02's
  durable store ships, the default no-op sink logs events (coverage is honest: observed
  in logs, not yet durably recorded).
- Local auth remains a development/self-hosted mode: a single shared token maps to one
  user, so multi-owner separation requires an external IdP (Clerk) mode.
