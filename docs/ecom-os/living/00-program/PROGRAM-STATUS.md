---
owner: A00
baseline_commit: SET_BASELINE_SHA
coordination_branch: coordination/program
last_verified_against: SET_COMMIT_OR_BRANCH_SET
---

# Programme Status

| Agent | Branch | Status | Current deliverable | Open blocker | Ready evidence |
|---|---|---|---|---|---|
| A00 | `coordination/program` | discovery | Establish programme view | None | n/a |
| A01 | `agent/A01-platform-foundation` | not_started | Platform/identity contracts | — | — |
| A02 | `agent/A02-durable-core` | not_started | Durable core | — | — |
| A03 | `agent/A03-hermes-integration` | not_started | Hermes bridge/chat | — | — |
| A04 | `agent/a04-cs` | implementing | Connector/read model | A02 inbox/action ports, A06 UI, A03 catalog (IR-A04-01..05) | 33 A04 tests + full suite (578) green; migration N-1 round-trip; see A04 VERIFICATION.md |
| A05 | `agent/A05-customer-service` | not_started | CS/autonomy | — | — |
| A06 | `agent/A06-design-system` | not_started | UI source of truth | — | — |
| A07 | `agent/A07-operator-workspace` | not_started | Today/tasks/knowledge | — | — |
| A08 | `agent/A08-finance-brief` | not_started | Finance/daily brief | — | — |
| A09 | `agent/A09-production-integration` | not_started | Production/integration | — | — |

## Current programme statement

Replace this text with a concise description of what is integrated, what is independently
ready, what is blocked, and the next safe merge boundary. Do not append weekly summaries.
