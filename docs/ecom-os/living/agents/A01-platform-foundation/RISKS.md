# A01 — Platform Foundation and Identity — Current Risks and Edge Cases

| ID | Risk/edge case | Impact | Current mitigation/test | Owner | Status |
|---|---|---|---|---|---|
| A01-R01 | No explicit owner bootstrap; `ensure_member_for_user` (`app/services/organizations.py:276`) auto-makes every new user `owner` of an auto-created org | Anyone authenticating becomes owner; bootstrap never closes (violates `05-OPS` §3.1, Build Spec Slice 1) | Planned slice 4: single-owner gate that closes + host-only reopen; replay test | A01 | open |
| A01-R02 | Money stored as `float` (`app/models/refunds.py:32`) | Rounding/precision errors in money path (violates AGENTS I-16) | Planned `Money` type (int minor units + ISO); migrate refund amount; no-float unit test | A01 | open |
| A01-R03 | Timestamps are **naive** UTC (`app/core/time.py`) | Ambiguous tz at boundaries; spec wants UTC storage + tz-aware | Reshape to tz-aware UTC helpers; round-trip test; migrate cautiously (compat) | A01 | open |
| A01-R04 | No runtime typed-error envelope; handler emits `{detail,request_id}`; `code/retryable` only in opt-in docs | Inconsistent client error handling; missing normative codes | Planned `Error` envelope + 15-code enum (§10); ≥1 endpoint emits it; tests | A01 | open |
| A01-R05 | Health endpoints return `{ok:true}` with no checks (`app/main.py:498-549`) | False "ready"; can't distinguish liveness/readiness/degraded (violates `05-OPS` §11.1) | Planned multi-dimension `/health`; DB/migration/queue probes | A01 | open |
| A01-R06 | A02 audit/trace sink not available; identity/config changes must be audited | Cannot record required audit on day 1 | A01-owned no-op `AuditTraceSink` port + test fake; swap when A02 ships; interface request filed | A01/A02 | open |
| A01-R07 | Service-identity (agent) token lookup is O(n) full scan (`app/core/agent_auth.py:51`) | Latency/DoS surface as identities grow | Indexed lookup (key id prefix → row) when reshaping service identities | A01 | open |
| A01-R08 | IDs are `uuid4`, not UUIDv7 (all models) | Non-sortable IDs (AGENTS §6 "globally unique sortable") | New tables use UUIDv7; existing tables retained (no big-bang); document deviation | A01 | open |
| A01-R09 | Repo layout conflict: AGENTS.md §10 (`backend/{api,domain,application,infrastructure}`, `packages/contracts`) vs `03-ENGINEERING.md` §2 (`backend/app/{...}`, `hermes-integration/`) vs actual `backend/app/{...}` | Wrong early move breaks the working prototype | No rename until resolved; decision request to A00/human; AGENTS.md wins by precedence | A01/A00 | open |
| A01-R10 | `Gateway.token` stored unencrypted (`app/models/gateways.py:25`) | Plaintext secret in DB (violates AGENTS I-15) | Route through Fernet `secret_store`/handle; secret-detection corpus in CI | A01 | open |
| A01-R11 | On-disk branch `agent/a01-foundation` ≠ docs branch `agent/A01-platform-foundation` | Integration/tooling that keys on branch name may mismatch | Stay on current branch per launch instruction; note for A09 integration | A01/A09 | open |
| A01-R12 | Heavy openclaw/board-orchestration baggage (`services/openclaw/`, gateways, boards, souls) | Scope confusion; dead weight; package still named `openclaw-agency-backend` | Wall off, do not strip in discovery; mark canonical/facade/deprecated as verticals migrate | A01 | open |

Delete resolved rows after the durable behaviour/test/documentation is in place.
