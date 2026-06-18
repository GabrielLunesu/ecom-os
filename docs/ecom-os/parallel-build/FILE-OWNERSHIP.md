# File and Surface Ownership

Ownership prevents parallel agents from solving merge conflicts by silently overwriting
one another. It does not prevent an owner from accepting a documented interface request.

## Backend ownership

| Area | Owner | Typical paths |
|---|---|---|
| Shared types, auth, request context, API contracts | A01 | `backend/app/auth/`, `backend/app/core/`, common domain types, `packages/contracts/` |
| Inbox/outbox, Postgres jobs, trace/action/evidence/incident platform | A02 | `backend/app/events/`, `jobs/`, `actions/`, `traces/` |
| Hermes bridge, capability probe, tool transport/generator | A03 | `backend/app/hermes/`, `backend/app/tools/`, `hermes-integration/` |
| Provider adapters, connections, sync, commerce models | A04 | `backend/app/connectors/`, commerce/sync modules |
| Tickets, CS workflows, policies, grants, approvals | A05 | customer-service and autonomy modules |
| Today attention, tasks, documents/search | A07 | task, attention, and document modules |
| Metrics, financial snapshots, daily briefs | A08 | `backend/app/metrics/`, brief modules |
| Operations, extension host, backup/update/health | A09 | operations and extension modules |

A06 owns no business backend. It may add a development-only component-catalog endpoint
only through an A01-approved contract.

## Frontend route ownership

| Surface | Owner |
|---|---|
| Global shell, sidebar, theme, command palette, primitives, component lab | A06 |
| `/activity`, trace detail, incident detail | A02 |
| `/chat`, `/agents` | A03 |
| `/orders`, `/customers`, connection settings | A04 |
| `/customer-service`, ticket detail, `/approvals`, autonomy settings | A05 |
| `/`, `/tasks`, `/knowledge` | A07 |
| `/finance`, daily-brief detail/widgets | A08 |
| `/system`, extension/update/backup operations | A09 |
| owner bootstrap, login, team/role management | A01 |

A route owner uses A06 primitives and does not create an alternative design system.

## Controlled shared files

| File family | Owner | Other agents do this instead |
|---|---|---|
| root `AGENTS.md`, normative specs | Human/accepted ADR process | Open `DECISION-REQUESTS.md` |
| central backend app/router registration | A01, final integration by A09 | Export a domain router and request registration |
| generated API client/contracts | A01 | Change owned schemas and request regeneration |
| `frontend/package.json`, UI lockfile, Tailwind/theme config | A06 | Request a dependency/token/component |
| backend dependency/lock files | A01 | Request a dependency with rationale |
| global frontend layout/sidebar/navigation | A06 | Add a navigation request |
| compose, Dockerfiles, deployment/update/backup scripts, CI | A09 | State runtime requirement in interface request |
| Hermes adapter package metadata | A03 | Add a transport/tool request |
| integration migration merge revisions | A09 | Add only domain-owned migration revisions |

## Migration protocol

- Every domain agent may add migrations for tables it owns.
- Never edit an already-merged migration.
- Use descriptive revision names prefixed with the agent ID.
- Parallel heads are allowed on feature branches; A09 creates the explicit merge revision
  on the integration branch.
- Each migration includes upgrade tests and realistic data fixtures.
- Cross-domain foreign keys require an accepted interface entry before implementation.

## Dependency protocol

A builder does not edit another owner's lockfile. Record the exact package, version range,
reason, security/maintenance impact, and affected tests in `INTERFACE-REQUESTS.md`. The
owner either adds it or documents the rejection and supported alternative.
