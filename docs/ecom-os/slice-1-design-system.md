# Ecom-OS — Slice 1: Design system + app shell

Implements Build Spec §3 (design system) and §7/§8.1 (app shell, store switcher,
⌘K palette, page-transition layout).

## What shipped
- **Centralized tokens** — `frontend/src/lib/design/tokens.ts` is the single source
  for color, typography, elevation, radius, and motion (duration/easing/spring).
  CSS custom properties in `globals.css` mirror the same values.
- **Typography** — switched the whole product to **Inter** with tight tracking
  (headings `-0.02em`) and **tabular figures** enabled globally so KPIs/tables never
  reflow. Legacy `font-heading/body/display` classes now all resolve to Inter.
- **Elevation** — soft, low-opacity layered shadows (`shadow-card/panel/overlay`).
  No hard drop shadows.
- **Motion (Framer Motion)** — animated page/route transitions (`PageTransition`),
  list stagger, a sliding active-nav pill (`layoutId`), spring hover on KPI cards,
  and an animated KPI counter (`AnimatedNumber`). `prefers-reduced-motion` is honored
  globally in `globals.css`.
- **App shell** — `EcomShell` = sidebar (`EcomSidebar`) + top bar with the global
  **store switcher** (`StoreSwitcher`: "All stores" aggregate + each store) + ⌘K
  **command palette** (`CommandPalette`) for navigation and store switching.
- **IA routes** — route group `frontend/src/app/(ecom)/` renders Overview, Analytics,
  Tasks, Chat, CS, Brand inside the shell. Agents/Settings reshape into the shell in
  their own slices.

## Store scope
`store-context.tsx` holds the active store (or aggregate), persisted to
`localStorage`. Slice 2 replaces the seed store list with the backend stores
endpoint (Composio/connection refs) — the context shape is unchanged.

## Verify
- `cd frontend && npx tsc --noEmit` → 0 errors
- `npx eslint src/components/ecom src/lib/design 'src/app/(ecom)'` → clean
- `npm run build` → succeeds; `/overview /analytics /tasks /chat /cs /brand` prerender.

## Notes / deviations
- Shopify is connected via a **direct Admin API token** (Composio's managed OAuth was
  unavailable). See `docs/ecom-os/bootstrap.md` and `scripts/bootstrap/shopify_oauth.py`.
