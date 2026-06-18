# A07 — Today, Tasks, Knowledge, and Operator Workspace Handoff

**Branch:** `agent/A07-operator-workspace`

## Mission

Build the calm operator layer that turns traces, tickets, metrics, tasks, incidents, approvals, and documents into actionable attention and contextual work.

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

- Today attention model and home route; deterministic ranking explanation.
- Tasks/assignees/entity links/comments/provenance and task tools/routes.
- Document/version/access/trust/ingestion/full-text search and Knowledge route/tools.
- Contextual “Ask Hermes” launches and entity context chips/panels specific to these surfaces.

## Explicitly out of scope

- Do not duplicate Hermes chat/session transport (A03).
- Do not calculate financial metrics (A08), own CS workflow (A05), or create global UI primitives (A06).
- Do not expose restricted document content/counts before role filtering.
- Do not require a vector database for v1.

## Work packages

1. Audit current Overview/Tasks/Brand-vault/copilot/context behavior and map useful models/components to v2.
2. Implement tasks with human/agent provenance, assignee/due/priority/status/entity links, comments/activity, trace link, daily-brief inclusion, and server-side access control.
3. Implement versioned documents with source/effective date/owner/access/trust labels, extraction status, Postgres FTS, supersession, role-test retrieval, and evidence links.
4. Expose document/task tools through A03 catalog registration and contextual chat launches that pass safe entity references rather than duplicate transcripts.
5. Build Today from deterministic attention inputs: approvals, incidents, failed/unknown actions, health, CS backlog, due tasks, and brief/metric signals. Explain why each item ranks.
6. Build Today/Tasks/Knowledge routes with A06 states and links back to source entities/traces.
7. Compose inputs defensively so missing A05/A08 sources degrade as unavailable, not zero.

## Cross-agent contracts

Consume A01 identity, A02 traces/incidents/jobs, A03 session/context launch, A05 CS attention events, A08 brief/metric snapshots, A06 UI. Expose TaskService, DocumentSearch/Get, AttentionItem/Explanation, and brief task inputs.

## Ready-for-integration acceptance

- [ ] Every Today item links to its source/trace and has a deterministic ranking explanation.
- [ ] Role-restricted cards and document search do not leak counts, snippets, or content.
- [ ] Agent-created tasks carry actor/run/trace provenance.
- [ ] Superseded SOP versions remain identifiable for historical trace inspection.
- [ ] Postgres full-text search works without mandatory embeddings.
- [ ] Contextual Ask Hermes opens/resumes canonical A03 sessions with safe entity references.

## Common traps

- Building a cosmetic dashboard that hides missing/degraded inputs.
- Using an LLM to rank operational attention without deterministic reasons.
- Treating the document vault as all of Hermes memory.

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
