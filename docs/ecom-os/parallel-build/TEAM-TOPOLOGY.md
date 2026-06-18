# Team Topology — Ten Agents

## Recommendation

Launch **10 agents**. This is the smallest team that keeps the load-bearing systems in
separate ownership lanes while retaining an independent auditor and an integration owner.

| ID | Role | Primary build slices | Code owner |
|---|---|---|---|
| A00 | Program auditor | All gates, no feature implementation | No — programme docs only |
| A01 | Platform foundation and identity | Slice 1 + shared contracts | Yes |
| A02 | Durable events, jobs, traces, and actions | Slices 2 and 8 | Yes |
| A03 | Hermes native integration and main chat | Slices 0, 3, channel transport in 11 | Yes |
| A04 | Commerce connectors and operational read models | Slice 4 | Yes |
| A05 | Customer service, approvals, and autonomy | Slices 5–7 | Yes |
| A06 | Design system and application shell | UI foundation for every slice | Yes |
| A07 | Today, tasks, knowledge, and operator workspace | Slices 9 and 12 | Yes |
| A08 | Finance, metric evidence, and daily brief | Slices 10 and 11 | Yes |
| A09 | Production operations, extensions, integration, and quality | Slice 13 + release gates | Yes |

## Dependency graph

```mermaid
graph TD
  A01[A01 Platform] --> A02[A02 Durable core]
  A01 --> A03[A03 Hermes]
  A01 --> A04[A04 Commerce]
  A01 --> A05[A05 CS]
  A01 --> A07[A07 Workspace]
  A01 --> A08[A08 Finance]
  A06[A06 UI system] --> A02
  A06 --> A03
  A06 --> A04
  A06 --> A05
  A06 --> A07
  A06 --> A08
  A02 --> A03
  A02 --> A04
  A02 --> A05
  A02 --> A07
  A02 --> A08
  A03 --> A05
  A03 --> A07
  A03 --> A08
  A04 --> A05
  A04 --> A08
  A05 --> A07
  A08 --> A07
  A01 --> A09[A09 Production and integration]
  A02 --> A09
  A03 --> A09
  A04 --> A09
  A05 --> A09
  A06 --> A09
  A07 --> A09
  A08 --> A09
  A00[A00 Auditor] -. observes .-> A01
  A00 -. observes .-> A02
  A00 -. observes .-> A03
  A00 -. observes .-> A04
  A00 -. observes .-> A05
  A00 -. observes .-> A06
  A00 -. observes .-> A07
  A00 -. observes .-> A08
  A00 -. observes .-> A09
```

Dependencies do not mean downstream agents wait idly. They start by auditing the current
implementation, defining their contracts, building fixtures and isolated domain logic,
and recording exact interface requests. They merge only when the required upstream
contract is available.

## Why not fewer

- Combining A02 and A05 makes the action ledger subordinate to one workflow instead of a
  platform primitive.
- Combining A03 and A05 recreates a Hermes wrapper rather than a peer integration.
- Combining A04 and A08 confuses connector normalization with financial definitions.
- Combining A06 with product-page work makes every UI branch edit the same tokens, shell,
  and primitives.
- Combining A00 and A09 removes independent review: the same agent would judge its own
  integration work.

## Why not more

The remaining boundaries are tightly coupled enough that extra agents would split a
single data model or route family and create more merge conflicts than throughput.
