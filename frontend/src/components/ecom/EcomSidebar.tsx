"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { spring } from "@/lib/design/tokens";
import { NAV_ITEMS } from "./nav-items";

/** Primary navigation. A single shared `layoutId` pill slides between items as
 * the route changes (Framer Motion layout animation, Build Spec §3). */
export function EcomSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[248px] flex-col border-r border-[color:var(--border)] bg-[color:var(--surface)]">
      <div className="flex h-14 items-center gap-2.5 px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[color:var(--accent)] text-sm font-bold text-white">
          E
        </div>
        <span className="text-[15px] font-semibold tracking-[-0.02em] text-strong">
          Ecom-OS
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active =
            item.href === "/overview"
              ? pathname === "/overview"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "text-[color:var(--accent)]" : "text-muted hover:text-strong",
              )}
            >
              {active ? (
                <motion.span
                  layoutId="nav-active"
                  transition={spring.default}
                  className="absolute inset-0 rounded-lg bg-[color:var(--accent-soft)]"
                />
              ) : null}
              <Icon className="relative z-10 h-[18px] w-[18px]" />
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 text-[11px] text-quiet">
        <kbd className="rounded border border-[color:var(--border-strong)] bg-[color:var(--surface-muted)] px-1.5 py-0.5 font-sans">
          ⌘K
        </kbd>{" "}
        command palette
      </div>
    </aside>
  );
}
