"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Store as StoreIcon, XCircle } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { cn } from "@/lib/utils";
import { listContainer, listItem } from "@/lib/design/tokens";
import { useConnections, useStores } from "@/lib/ecom-api";

export default function SettingsPage() {
  const connections = useConnections();
  const stores = useStores();

  const ready = connections.data?.ready ?? false;

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Store connections, team, branding, runtime"
      />

      {/* Connections (Build Spec §1.5) — provider status, never secrets. */}
      <section className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-[-0.01em] text-strong">
            Connections
          </h2>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium",
              ready
                ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
                : "bg-[color:var(--warning)]/10 text-[color:var(--warning)]",
            )}
          >
            {ready ? "CS loop ready" : "CS loop blocked"}
          </span>
        </div>
        <motion.div
          variants={listContainer}
          initial="hidden"
          animate="show"
          className="grid gap-3 sm:grid-cols-2"
        >
          {(connections.data?.providers ?? []).map((p) => (
            <motion.div
              key={p.provider}
              variants={listItem}
              className="flex items-center gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
            >
              {p.connected ? (
                <CheckCircle2 className="h-5 w-5 text-[color:var(--success)]" />
              ) : (
                <XCircle className="h-5 w-5 text-[color:var(--danger)]" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium capitalize text-strong">
                  {p.provider}
                </p>
                <p className="truncate text-xs text-quiet">{p.detail}</p>
              </div>
            </motion.div>
          ))}
          {connections.isLoading ? (
            <div className="h-[68px] animate-pulse rounded-xl bg-[color:var(--surface-muted)]" />
          ) : null}
        </motion.div>
      </section>

      {/* Stores — connection refs only. */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold tracking-[-0.01em] text-strong">
          Stores
        </h2>
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card">
          {(stores.data ?? []).map((s, i) => (
            <div
              key={s.id}
              className={cn(
                "flex items-center gap-3 px-4 py-3",
                i > 0 && "border-t border-[color:var(--border)]",
              )}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                <StoreIcon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-strong">{s.name}</p>
                <p className="truncate text-xs text-quiet">{s.domain}</p>
              </div>
              <span className="text-xs text-quiet">{s.provider}</span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                  s.status === "connected"
                    ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
                    : "bg-[color:var(--surface-muted)] text-muted",
                )}
              >
                {s.status}
              </span>
            </div>
          ))}
          {!stores.isLoading && (stores.data ?? []).length === 0 ? (
            <p className="px-4 py-6 text-sm text-quiet">No stores connected yet.</p>
          ) : null}
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        {[
          { t: "Team", d: "Members & CS rep handoff", s: "slice 8" },
          { t: "Branding", d: "Logo, accent, theme tokens", s: "slice 1+" },
          { t: "Runtime", d: "AgentRuntime selection", s: "slice 9" },
        ].map((c) => (
          <div
            key={c.t}
            className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
          >
            <p className="text-sm font-medium text-strong">{c.t}</p>
            <p className="mt-0.5 text-xs text-quiet">{c.d}</p>
            <span className="mt-2 inline-block rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[11px] font-medium text-[color:var(--accent)]">
              {c.s}
            </span>
          </div>
        ))}
      </section>
    </div>
  );
}
