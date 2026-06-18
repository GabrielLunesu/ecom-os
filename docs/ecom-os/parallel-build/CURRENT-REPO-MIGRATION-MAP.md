# Current Repository → V2 Migration Map

The current repository already contains a working Next.js/FastAPI/Postgres application,
customer-service flows, connector code, deployment scripts, and an initial Hermes gateway
path. Preserve useful behavior and tests. Do not perform a big-bang rewrite merely to
match target folder names.

## Current assets to retain and reshape

- Existing Next.js pages and Radix/Tailwind components are migration inputs for A06 and
  route owners.
- Existing tasks/Kanban, ticket UI, flow builder, prompts, connectors, and deploy scripts
  should be evaluated for reuse.
- Existing Hermes `/delegate` or gateway work is a spike/input for A03, not the final
  transport contract by itself.
- Existing CS flows are valuable product behavior, but every send/discount/refund must
  move behind the v2 action, trace, identity, and autonomy contracts.
- Existing local auth may remain a development/bootstrap mode; it is not a substitute for
  the v2 owner/role/service/channel identity model.

## Required architectural migrations

| Current tendency | V2 direction | Owner |
|---|---|---|
| In-app `AgentRuntime`/CS runtime decides model path | Hermes is an independent peer behind `HermesBridge` | A03 |
| Read-only/copied chat behavior | Canonical Hermes sessions and history | A03 |
| Redis/RQ worker path | Postgres leased jobs for v1 | A02; compose cleanup A09 |
| Connector call as workflow completion | Durable action + attempts + reconciliation | A02/A04/A05 |
| Legacy activity feed | Trace/action/evidence/incident explorer | A02 |
| Old fixed safety tiers/no-refund invariant | Owner-selected grants including honest unrestricted mode | A05 |
| Revenue-first/general analytics | Evidenced estimated contribution margin | A08 |
| Ad-hoc UI styling | Extracted shadcn/Radix system from `dashboard-inspo/` | A06 |
| Database-only backup/update script | Full Ecom-OS + Hermes profile restore/update path | A09 |
| Broad settings without identity mapping | Human, service, and channel identities | A01/A03 |

## Migration method

1. Add stable ports and v2 records beside existing behavior.
2. Backfill/migrate data with tested migrations.
3. Route one vertical slice through the new contract.
4. Compare output and traces against the old path.
5. switch behind a feature flag;
6. remove old behavior only after acceptance and restore tests pass.

A source path may remain temporarily as a compatibility facade. The living document must
state whether it is canonical, a facade, deprecated, or pending removal.
