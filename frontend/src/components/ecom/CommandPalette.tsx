"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Layers, Store as StoreIcon } from "lucide-react";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command";
import { NAV_ITEMS } from "./nav-items";
import { ALL_STORES, useStore } from "./store-context";

/** ⌘K command palette: navigate the IA and switch store scope from anywhere
 * (Build Spec §3: keyboard-first, native feel). */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { stores, setActiveStoreId } = useStore();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const run = (fn: () => void) => {
    setOpen(false);
    fn();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-[60] bg-slate-950/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]">
          <DialogPrimitive.Content
            className="w-full max-w-xl overflow-hidden rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-overlay focus:outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
            aria-label="Command palette"
          >
            <DialogPrimitive.Title className="sr-only">Command palette</DialogPrimitive.Title>
            <Command>
              <CommandInput placeholder="Search pages, switch store…" autoFocus />
              <CommandList className="max-h-[360px] p-1">
                <CommandEmpty className="text-muted">No results.</CommandEmpty>
                <CommandGroup heading="Navigate">
                  {NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    return (
                      <CommandItem
                        key={item.href}
                        value={`${item.label} ${item.description}`}
                        onSelect={() => run(() => router.push(item.href))}
                      >
                        <Icon className="mr-2.5 h-4 w-4 text-muted" />
                        <span className="text-strong">{item.label}</span>
                        <span className="ml-2 truncate text-xs text-quiet">
                          {item.description}
                        </span>
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
                <CommandGroup heading="Store scope">
                  <CommandItem
                    value="all stores aggregate"
                    onSelect={() => run(() => setActiveStoreId(ALL_STORES))}
                  >
                    <Layers className="mr-2.5 h-4 w-4 text-muted" />
                    <span className="text-strong">All stores</span>
                    <CommandShortcut>aggregate</CommandShortcut>
                  </CommandItem>
                  {stores.map((s) => (
                    <CommandItem
                      key={s.id}
                      value={`store ${s.name} ${s.domain}`}
                      onSelect={() => run(() => setActiveStoreId(s.id))}
                    >
                      <StoreIcon className="mr-2.5 h-4 w-4 text-muted" />
                      <span className="text-strong">{s.name}</span>
                      <CommandShortcut>{s.domain}</CommandShortcut>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </DialogPrimitive.Content>
        </div>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
