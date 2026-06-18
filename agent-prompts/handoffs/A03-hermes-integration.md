# A03 — Hermes Native Integration and Main Chat Handoff

**Branch:** `agent/A03-hermes-integration`

## Mission

Make Hermes a first-class independent peer: canonical sessions in the dashboard, supported background runs, generated Ecom-OS tools, native channel/cron delivery, capability negotiation, and trace correlation.

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

- `backend/app/hermes/**`, canonical Ecom-OS tool-catalog framework, `hermes-integration/**`, conformance fixtures.
- Hermes profile/session references and compatibility records, not Hermes-native state itself.
- Frontend `/chat` and `/agents`, streamed tool/action cards, reconnect/interrupt/context drawer.
- Native channel and cron transport/setup contracts used by A08.

## Explicitly out of scope

- Never read/write Hermes private `state.db`, memory files, profile internals, or vendor-patch Hermes.
- Do not duplicate canonical Hermes transcripts in Postgres.
- Do not store current orders/tickets/metrics as Hermes truth.
- Do not implement domain authorization/policy inside the adapter.

## Work packages

1. Audit all current `AgentRuntime`, `CS_RUNTIME`, `/delegate`, MCP, Hermes docs/scripts, session/chat code, and identify reusable spikes versus unsupported assumptions.
2. Pin/test a Hermes range; implement capability probe and visible compatibility record. Missing capabilities degrade the dependent feature only.
3. Implement `HermesBridge` transports for canonical interactive sessions and documented background runs, including stream events, reconnect/status/history, interruption, leases, and failure recovery.
4. Generate adapter/MCP schemas from one canonical catalog; domain agents supply owned tool definitions without hand-maintained duplicate schemas.
5. Correlate Hermes profile/session/run/turn/tool identifiers to A02 traces while labeling non-Ecom activity only observed/imported/unknown as justified.
6. Build the main Chat and Agents surfaces. Browser receives only approved product operations, never a privileged Hermes service token.
7. Implement native channel identity/destination and cron/delivery transport contracts plus a real conformance message; A08 owns brief content/numbers.

## Cross-agent contracts

Consume A01 service/channel identity and A02 trace/tool/action records. Expose HermesBridge, BackgroundRunPort, SessionReference, capability flags, tool transport/generator, narration request, ChannelDeliveryPort, and SchedulePort.

## Ready-for-integration acceptance

- [ ] A canonical Hermes session can be created/resumed and streamed in `/chat`; reconnect queries real status/history.
- [ ] One Ecom-OS read tool appears in Hermes and creates a verified invocation/trace.
- [ ] Native non-Ecom tool activity is not mislabeled verified.
- [ ] One background run and one native channel delivery pass against the pinned runtime.
- [ ] No direct Hermes SQLite/profile mutation exists.
- [ ] Conformance failures are actionable and visible in `/agents`/System health.

## Common traps

- Treating a profile as a security sandbox.
- Proxying arbitrary Hermes protocol methods to the browser.
- Making the existing `/delegate` spike the architecture without validating current official protocols.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
