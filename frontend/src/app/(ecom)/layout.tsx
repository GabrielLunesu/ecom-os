import type { ReactNode } from "react";

import { EcomShell } from "@/components/ecom/EcomShell";

/** Layout for the Ecom-OS product surface — every page in this route group
 * renders inside the shell (sidebar, store switcher, ⌘K, page transitions). */
export default function EcomLayout({ children }: { children: ReactNode }) {
  return <EcomShell>{children}</EcomShell>;
}
