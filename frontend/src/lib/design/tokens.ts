/**
 * Ecom-OS design tokens — the single source of truth for the whole UI.
 *
 * Everything visual (color, type, elevation, radius, motion) is defined here so
 * the product is themeable from one place (Build Spec §3). CSS custom properties
 * mirror these in `globals.css`; this module exposes the same values to TS for
 * Framer Motion, inline styles, and animated counters.
 */

// ---------------------------------------------------------------------------
// Motion — one shared set of duration/easing/spring tokens (Build Spec §3).
// Consumed by page transitions, enter/exit, layout, list reorder, KPI counters.
// ---------------------------------------------------------------------------
export const duration = {
  fast: 0.15,
  base: 0.22,
  slow: 0.4,
  slower: 0.6,
} as const;

/** Cubic-bezier easings (Material "emphasized"/"standard" family). */
export const easing = {
  standard: [0.2, 0, 0, 1] as [number, number, number, number],
  emphasized: [0.2, 0, 0, 1] as [number, number, number, number],
  exit: [0.4, 0, 1, 1] as [number, number, number, number],
  inOut: [0.4, 0, 0.2, 1] as [number, number, number, number],
} as const;

/** Spring presets for 60fps micro-interactions and layout animation. */
export const spring = {
  /** General-purpose layout + shared-element springs. */
  default: { type: "spring", stiffness: 380, damping: 32, mass: 0.9 },
  /** Snappy press/hover feedback. */
  snappy: { type: "spring", stiffness: 560, damping: 30, mass: 0.7 },
  /** Gentle, low-overshoot for large surfaces. */
  gentle: { type: "spring", stiffness: 220, damping: 30, mass: 1 },
} as const;

/** Page/route transition variants — used by the shell's AnimatePresence wrapper. */
export const pageTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
  transition: { duration: duration.base, ease: easing.standard },
} as const;

/** Stagger container/item variants for list enter animations. */
export const listContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04, delayChildren: 0.02 } },
} as const;

export const listItem = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: duration.base, ease: easing.standard } },
} as const;

// ---------------------------------------------------------------------------
// Typography — Inter, tight tracking, tabular figures (Build Spec §3).
// ---------------------------------------------------------------------------
export const typography = {
  fontFamily: 'var(--font-sans), "Inter", system-ui, -apple-system, sans-serif',
  tracking: {
    /** Headings: tight. */
    heading: "-0.02em",
    headingTight: "-0.03em",
    /** Body: slightly tight. */
    body: "-0.01em",
    normal: "0",
  },
  /** Apply to every numeric/KPI surface. */
  tabularNums: '"tnum" 1, "lnum" 1',
} as const;

// ---------------------------------------------------------------------------
// Color — light, calm surface palette. Mirrored as CSS vars in globals.css.
// ---------------------------------------------------------------------------
export const color = {
  bg: "#f7f8fa",
  surface: "#ffffff",
  surfaceMuted: "#f1f3f6",
  surfaceStrong: "#e7eaf0",
  border: "#eceef2",
  borderStrong: "#dce0e8",
  text: "#0b1220",
  textMuted: "#5b6577",
  textQuiet: "#9aa3b2",
  accent: "#4f46e5",
  accentStrong: "#4338ca",
  accentSoft: "rgba(79, 70, 229, 0.10)",
  success: "#0f9d58",
  warning: "#d98a04",
  danger: "#dc2626",
} as const;

// ---------------------------------------------------------------------------
// Elevation — soft, low-opacity layered shadows. No hard drop shadows.
// ---------------------------------------------------------------------------
export const shadow = {
  xs: "0 1px 2px rgba(11,18,32,0.04)",
  sm: "0 1px 2px rgba(11,18,32,0.05), 0 1px 3px rgba(11,18,32,0.04)",
  card: "0 1px 2px rgba(11,18,32,0.04), 0 4px 12px rgba(11,18,32,0.05)",
  panel: "0 2px 6px rgba(11,18,32,0.05), 0 12px 32px rgba(11,18,32,0.06)",
  overlay: "0 8px 24px rgba(11,18,32,0.10), 0 24px 56px rgba(11,18,32,0.12)",
} as const;

export const radius = {
  sm: "8px",
  md: "10px",
  lg: "14px",
  xl: "20px",
  pill: "999px",
} as const;

export const tokens = {
  duration,
  easing,
  spring,
  pageTransition,
  listContainer,
  listItem,
  typography,
  color,
  shadow,
  radius,
} as const;

export type Tokens = typeof tokens;
export default tokens;
