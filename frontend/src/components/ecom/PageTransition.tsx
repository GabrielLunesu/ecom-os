"use client";

import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import type { ReactNode } from "react";

import { pageTransition } from "@/lib/design/tokens";

/** Animated route transitions for the app shell (Build Spec §3). Keyed on
 * pathname so each page enters/exits with the shared motion tokens. */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial={pageTransition.initial}
        animate={pageTransition.animate}
        exit={pageTransition.exit}
        transition={pageTransition.transition}
        className="h-full"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
