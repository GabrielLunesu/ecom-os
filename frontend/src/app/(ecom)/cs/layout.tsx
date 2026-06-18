"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** CS is a section, not a single page. These sub-pages live under it:
 * the live tickets board, the visual flow builder, and the prompt library. */
const CS_TABS = [
  { href: "/cs", label: "Tickets" },
  { href: "/cs/flows", label: "Flows" },
  { href: "/cs/prompts", label: "Prompts" },
];

export default function CsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div>
      <div className="mb-5 flex items-center gap-1 border-b border-[color:var(--border)]">
        {CS_TABS.map((t) => {
          const active = t.href === "/cs" ? pathname === "/cs" : pathname.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                "relative -mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "border-[color:var(--accent)] text-strong"
                  : "border-transparent text-muted hover:text-strong",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
