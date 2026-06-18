---
owner: A05
branch: agent/A05-customer-service
status: not_started
last_verified_commit: SET_ME
---

# A05 — Customer Service, Approvals, and Autonomy — Current State

## Mission

Evolve the existing CS system into the v2 traced workflow: tickets, WISMO shadow mode, drafts, reply actions, exact approvals, grants, policies, unrestricted mode, and sticky escalation.

## Ownership

**Owns:** ticket/message state and history, classification/workflow, proposals, assignment/escalation, send-reply and related action schemas, grants/policies/approvals, CS/Approvals/autonomy routes and tools.

**Does not own:** generic action ledger internals, connector implementations, Hermes protocol, global UI, finance.

## Current implementation

Replace this section after auditing the repository. State what exists, what is canonical,
what is a compatibility facade, and what is absent. Link exact source and tests.

## Current architecture

Describe the implementation as it exists at `last_verified_commit`; link `DIAGRAMS.md`.

## Dependencies

Consumes A01 identity, A02 action/trace/jobs, A03 Hermes background runs, A04 commerce/inbox, A06 UI.
