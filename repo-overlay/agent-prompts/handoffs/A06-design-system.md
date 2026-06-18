# A06 — Design System and Application Shell Handoff

**Branch:** `agent/A06-design-system`

## Mission

Make `dashboard-inspo/` the explicit design-language reference and convert it into a coherent, accessible Ecom-OS shadcn/Radix system used by every route.

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

- `frontend/src/components/ui/**`, shell/navigation/theme providers, global styles/tokens, command palette, page/state primitives, UI dependency lock.
- `docs/ecom-os/design/**` and a development component lab/visual fixture surface.
- Global layout/sidebar/nav integration requests from route owners.

## Explicitly out of scope

- Do not introduce multi-tenant data architecture. Adapt the visual tenant switcher to one-brand/multi-store context.
- Do not own domain APIs, state machines, or business page behavior.
- Do not leave runtime imports from `dashboard-inspo/` or create a second CSS/component system.
- Do not copy inaccessible components blindly.

## Work packages

1. Inventory every inspiration route/component/token/state/animation and current Ecom-OS UI component. Publish adopt/adapt/defer/reject matrix with source and destination paths.
2. Extract typed/CSS tokens for light/dark colors, typography, spacing, radii, shadows, chart/data colors, motion, density, focus and breakpoints.
3. Build/update shadcn/Radix primitives and compound operational patterns: shell, sidebar, store/context switcher, page header, filters, tables, KPI cards, entity/evidence/trace/action cards, drawers, dialogs, forms, skeleton/empty/error/stale/forbidden states.
4. Build command palette, responsive/mobile navigation, reduced-motion behavior, full keyboard focus, and no-FOUC theme setup.
5. Create component lab and visual/interaction tests for both themes and required states.
6. Migrate only global shell/shared components; route owners migrate domain pages and request missing patterns through the interface queue.
7. Document exactly how “multi-tenant” inspiration was semantically adapted without tenant IDs or organization switching.

## Cross-agent contracts

Expose stable component APIs, token names, layout slots, navigation registration request format, and route-state patterns. Consume typed API result/action/freshness shapes from A01/A02 as they stabilize.

## Ready-for-integration acceptance

- [ ] Every inspiration component/pattern has an explicit decision and no unexplained omissions.
- [ ] Light/dark themes, sidebar, store/context switching, command palette, and responsive shell work without FOUC.
- [ ] Component lab covers populated/loading/empty/error/stale/forbidden states and keyboard/reduced-motion behavior.
- [ ] Route owners can build without editing global tokens/primitives.
- [ ] No multi-tenant backend semantics or runtime dependency on the inspiration folder is introduced.
- [ ] Existing useful Ecom-OS pages can migrate incrementally without a full rewrite.

## Common traps

- Copying pixels but not interaction/error/accessibility behavior.
- Making each domain page own a variant of the same table/card/dialog.
- Treating “every component” as “every demo feature must ship in v1.”

## Required living-doc result

At every checkpoint, `CURRENT.md` states the real implementation and commit; `WORKBOARD.md` contains only current work; `INTERFACES.md` matches generated/runtime contracts; `RISKS.md` contains only open risks; `VERIFICATION.md` contains exact latest evidence; `HANDOFF.md` gives a safe continuation point.
