# Dashboard Inspiration → Ecom-OS UI Source of Truth

`dashboard-inspo/` is the visual and interaction reference. It is **not** imported as a
runtime package and it does not override Ecom-OS product semantics.

## A06 extraction process

1. Inventory every route, layout, component, primitive, token, state, animation, and
   responsive behavior in `dashboard-inspo/`.
2. Record each item in `docs/ecom-os/design/COMPONENT-CATALOG.md` as `adopt`, `adapt`,
   `defer`, or `reject`, with source path and Ecom-OS destination.
3. Extract foundations first: typography, spacing, radii, shadows, colors, data colors,
   motion, focus, density, light/dark behavior, and icon rules.
4. Build owned shadcn/ui + Radix primitives in Ecom-OS. Copying is allowed only after
   dependencies, accessibility, and licensing are understood; no live import from the
   inspiration folder remains.
5. Build the app shell: sidebar, headers, breadcrumbs, command palette, page container,
   responsive navigation, context switcher, loading/error/empty/degraded patterns.
6. Expose a development component lab and route matrix so every domain agent can verify
   all states without inventing new primitives.
7. Domain route owners migrate existing pages onto this system incrementally.

## Semantic adaptation

The inspiration dashboard's “multi-tenant” switcher must **not** introduce multi-tenant
business semantics. Ecom-OS remains one brand per instance. Adapt that pattern into:

- brand identity display;
- store/context selector where multiple stores exist;
- optional environment/profile indicator;
- future-safe visual slots without `tenant_id`, organization switching, or cross-brand
  data paths.

## UI invariants

- shadcn/ui and Radix are the primitive layer;
- all tokens are CSS variables or one typed token module;
- light and dark themes have equivalent information hierarchy and contrast;
- numbers use tabular figures;
- keyboard navigation and visible focus are mandatory;
- reduced motion is honored;
- operational data shows freshness, coverage, and trace links where specified;
- external actions show backend-accepted action state, never fabricated success;
- every route has loading, empty, error, stale/degraded, forbidden, and populated states;
- domain agents do not fork global components to change local styling.
