"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { pageTransition } from "@/lib/design/tokens";

/**
 * Per-navigation enter animation for the Ecom-OS surface. App Router remounts
 * `template.tsx` on every route change, so this gives a clean fade/slide-in
 * without the AnimatePresence `mode="wait"` that previously swallowed page
 * content until a refresh.
 */
export default function EcomTemplate({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={pageTransition.initial}
      animate={pageTransition.animate}
      transition={pageTransition.transition}
      className="h-full"
    >
      {children}
    </motion.div>
  );
}
