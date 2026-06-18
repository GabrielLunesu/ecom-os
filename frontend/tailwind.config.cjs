/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Map shadcn primitive tokens to the Ecom-OS theme vars so popovers,
        // command palette, and menus get a real surface (no transparent dropdowns).
        popover: "var(--surface)",
        "popover-foreground": "var(--text)",
        muted: "var(--surface-muted)",
        "muted-foreground": "var(--text-muted)",
        accent: "var(--accent-soft)",
        "accent-foreground": "var(--text)",
      },
      fontFamily: {
        // Single typeface (Inter) across the product. Legacy heading/body/display
        // keys are retained so existing classes keep resolving — all map to sans.
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        heading: ["var(--font-sans)", "Inter", "sans-serif"],
        body: ["var(--font-sans)", "Inter", "sans-serif"],
        display: ["var(--font-sans)", "Inter", "sans-serif"],
      },
      letterSpacing: {
        heading: "-0.02em",
        "heading-tight": "-0.03em",
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,18,32,0.04), 0 4px 12px rgba(11,18,32,0.05)",
        panel: "0 2px 6px rgba(11,18,32,0.05), 0 12px 32px rgba(11,18,32,0.06)",
        overlay:
          "0 8px 24px rgba(11,18,32,0.10), 0 24px 56px rgba(11,18,32,0.12)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
