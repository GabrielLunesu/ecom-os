# A08 — Finance, Metric Evidence, and Daily Brief Handoff

**Branch:** `agent/A08-finance-brief`

## Mission

Provide trustworthy operational economics and a quiet daily operating recap whose numbers are deterministic, evidenced, timezone-correct, and deliverable through Hermes-native channels.

## Required reading

Read root `AGENTS.md`; all normative files in `docs/ecom-os/specs/`; all files in
`docs/ecom-os/parallel-build/`; all programme living docs; every agent's `CURRENT.md` and
`INTERFACES.md`; then inspect the current implementation and Git history for this domain.
The normative v2 documents beat old READMEs and old implementation assumptions.

## Working method

Work on the assigned branch/worktree. Before substantial code, replace placeholders in
your living docs with an evidence-based current-state map, interfaces, risks, diagrams,
and verification plan. Build several focused, demonstrable slices rather than one mega
change. Never edit another agent's owned source or living docs. Use the programme interface
queue for cross-domain work. Preserve useful prototype behavior while moving it behind v2
contracts.

## Owned scope

- Economics input model above provider adapters, formula definitions/versioning, metric snapshots/components/evidence/coverage/freshness.
- Finance route and metric read tools/explain-context.
- Daily brief snapshot, sections, deterministic fallback rendering, narration request, delivery intent/idempotency/status, and brief UI widgets.

## Explicitly out of scope

- Never ask an LLM to calculate or source a number.
- Never label the v1 KPI audited/accounting profit; use estimated contribution margin.
- Do not implement native Slack/Telegram/etc transport (A03) or provider account binding (A04).
- Do not silently treat missing COGS/ad/fees/FX as zero coverage.

## Work packages

1. Audit current Overview/Analytics KPI code, data sources, currencies, date windows, and existing insight/cron behavior.
2. Define versioned metric formulas using integer minor units, ISO currency, timezone/window, FX basis, attribution window, source precedence, missing-component coverage, and evidence.
3. Implement normalized economics inputs/snapshots/components and reconciliation warnings using A04 read models/connectors.
4. Build Finance page, drill-downs, source coverage, formula/version display, trends, stale/missing warnings, and metric tools. “Explain change” gives A03 a snapshot; narration cannot alter numbers.
5. Implement deterministic daily snapshot for revenue context, estimated contribution, CS, actions, incidents, tasks, research/todos, health, and today priorities.
6. Use A03 for optional narration and native channel/cron delivery. Persist delivery intent/idempotency/status/trace; fallback renderer always works.
7. Expose brief/metric cards to A07 Today and ensure reruns do not duplicate delivery.

## Cross-agent contracts

Consume A01 Money/timezone, A02 jobs/traces/actions/evidence, A03 Narration/ChannelDelivery/Schedule ports, A04 commerce/economics sources, A05 CS summaries, A06 UI, A07 task inputs. Expose MetricSnapshot/Get/ExplainContext and DailyBrief/Get/Generate contracts.

## Ready-for-integration acceptance

- [ ] Formula fixtures use minor units and reconcile every displayed KPI to components/evidence.
- [ ] Missing or stale cost/ad/fee/FX inputs visibly reduce coverage; no false precision.
- [ ] Date windows and user timezone are explicit and tested around boundaries.
- [ ] Narration failure still creates a useful deterministic brief.
- [ ] A configured Hermes-native destination receives one idempotent brief and delivery failure is visible/retryable.
- [ ] No metric or brief number originates from model prose.

## Common traps

- Calling revenue minus partial known costs “profit.”
- Letting connector-specific fields become formula semantics.
- Having A08 call messaging platforms directly instead of Hermes.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
