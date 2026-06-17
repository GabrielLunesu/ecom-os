"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronsUpDown, Store as StoreIcon, Layers } from "lucide-react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { duration, easing } from "@/lib/design/tokens";
import { ALL_STORES, useStore, type StoreScope } from "./store-context";

/** Global store scope selector: "All stores" aggregate + each connected store. */
export function StoreSwitcher() {
  const { stores, activeStoreId, setActiveStoreId, activeStore, isAggregate } =
    useStore();
  const [open, setOpen] = useState(false);

  const label = isAggregate ? "All stores" : (activeStore?.name ?? "Select store");

  const choose = (id: StoreScope) => {
    setActiveStoreId(id);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Switch store"
          className="group flex h-9 items-center gap-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-2.5 text-sm font-medium text-strong shadow-sm transition-colors hover:border-[color:var(--border-strong)]"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
            {isAggregate ? (
              <Layers className="h-3.5 w-3.5" />
            ) : (
              <StoreIcon className="h-3.5 w-3.5" />
            )}
          </span>
          <span className="max-w-[140px] truncate">{label}</span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-quiet" />
        </button>
      </PopoverTrigger>
      <AnimatePresence>
        {open ? (
          <PopoverContent
            align="start"
            sideOffset={6}
            className="w-[240px] overflow-hidden p-0"
            asChild
            forceMount
          >
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.98 }}
              transition={{ duration: duration.fast, ease: easing.standard }}
            >
              <div className="px-3 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-quiet">
                Scope
              </div>
              <Row
                active={isAggregate}
                onClick={() => choose(ALL_STORES)}
                icon={<Layers className="h-4 w-4" />}
                title="All stores"
                subtitle={`Aggregate across ${stores.length}`}
              />
              <div className="my-1 h-px bg-[color:var(--border)]" />
              {stores.map((s) => (
                <Row
                  key={s.id}
                  active={activeStoreId === s.id}
                  onClick={() => choose(s.id)}
                  icon={<StoreIcon className="h-4 w-4" />}
                  title={s.name}
                  subtitle={s.domain}
                />
              ))}
            </motion.div>
          </PopoverContent>
        ) : null}
      </AnimatePresence>
    </Popover>
  );
}

function Row({
  active,
  onClick,
  icon,
  title,
  subtitle,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors",
        active ? "bg-[color:var(--accent-soft)]" : "hover:bg-[color:var(--surface-muted)]",
      )}
    >
      <span
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-md",
          active
            ? "bg-[color:var(--accent)] text-white"
            : "bg-[color:var(--surface-muted)] text-muted",
        )}
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-strong">{title}</span>
        <span className="block truncate text-xs text-quiet">{subtitle}</span>
      </span>
      {active ? <Check className="h-4 w-4 text-[color:var(--accent)]" /> : null}
    </button>
  );
}
