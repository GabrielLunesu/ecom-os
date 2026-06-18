"use client";

import type { ReactNode } from "react";

import { StoreProvider } from "./store-context";
import { EcomSidebar } from "./EcomSidebar";
import { StoreSwitcher } from "./StoreSwitcher";
import { CommandPalette } from "./CommandPalette";

/** The Ecom-OS application shell: fixed sidebar, top bar with the global store
 * switcher, ⌘K palette, and animated page transitions (Build Spec §3, §7). */
export function EcomShell({ children }: { children: ReactNode }) {
  return (
    <StoreProvider>
      <div className="flex h-screen overflow-hidden bg-[color:var(--bg)]">
        <EcomSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-[color:var(--border)] bg-[color:var(--surface)]/80 px-6 backdrop-blur">
            <StoreSwitcher />
            <div className="flex-1" />
            <div className="text-sm text-quiet">Chicago Outlet · Ops</div>
          </header>
          <main className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-[1280px] px-6 py-6">{children}</div>
          </main>
        </div>
        <CommandPalette />
      </div>
    </StoreProvider>
  );
}
