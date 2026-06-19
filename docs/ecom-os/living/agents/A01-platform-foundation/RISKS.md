# A01 — Platform Foundation and Identity — Current Risks and Edge Cases

Resolved during the foundation build (durable behaviour + tests in place), kept here
only as a pointer until integration: R01 owner-bootstrap closure, R04 typed errors, R05
health, R07 service-token O(1) lookup — see VERIFICATION.md.

| ID | Risk/edge case | Impact | Current mitigation/test | Owner | Status |
|---|---|---|---|---|---|
| A01-R02 | Prototype money stored as `float` (`app/models/refunds.py:32`) | Precision errors in money path (I-16) | Canonical `Money` type shipped (`app/core/money.py`); refund column not yet migrated — do it via A08's vertical, not a mass migration | A01/A08 | open (type ready, retrofit deferred) |
| A01-R03 | Prototype timestamps are naive UTC (`app/core/time.py:utcnow`) | Ambiguous tz at boundaries | tz-aware helpers added (`now_utc`/`ensure_utc`/`to_timezone`); existing columns intentionally unchanged | A01 | open (helpers ready, retrofit deferred) |
| A01-R06 | A02 audit/trace sink not available | Identity/config audit not durably stored yet | No-op `AuditTraceSink` port logs events honestly (coverage=observed); swap when A02 ships; interface request to file | A01/A02 | open (port in place) |
| A01-R08 | New tables use UUIDv7 but prototype tables remain `uuid4` | Mixed ID schemes | Documented deliberate choice (no big-bang); new identity tables sortable | A01 | accepted |
| A01-R09 | Repo-layout conflict: AGENTS.md §10 vs `03-ENGINEERING.md` §2 vs actual `backend/app/{...}` | Wrong early move breaks prototype | No rename done; added `app/auth/` + `app/core/` behind seams; decision request to A00/human still open | A01/A00 | open |
| A01-R10 | `Gateway.token` stored unencrypted (`app/models/gateways.py:25`) | Plaintext secret in DB (I-15) | A03-owned (Hermes gateway); not edited by A01 — filed as interface request to route through secret store; redaction corpus catches log/response leaks meanwhile | A03 | open (handed off) |
| A01-R11 | On-disk branch `agent/a01-foundation` ≠ docs branch `agent/A01-platform-foundation` | Branch-name-keyed tooling may mismatch | Stay on current branch per launch instruction; flagged for A09 | A01/A09 | open |
| A01-R12 | Heavy openclaw/board-orchestration baggage (`services/openclaw/`, boards, gateways) | Scope confusion; package still named `openclaw-agency-backend` | Walled off, not stripped; A01 added beside it behind seams | A01 | accepted (defer cleanup) |
| A01-R13 | Concurrent owner-bootstrap claims race | Two owners if exactly simultaneous | `SELECT ... FOR UPDATE` on the singleton on Postgres serializes; sqlite no-op (tests single-threaded). Hardens further with a DB constraint if needed | A01 | open (low, mitigated on PG) |

Delete resolved rows after integration confirms the durable behaviour/test/docs.
