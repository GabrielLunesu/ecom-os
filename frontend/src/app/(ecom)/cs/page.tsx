"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Loader2, Play, ShieldCheck, User, X } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { duration, easing, spring } from "@/lib/design/tokens";
import {
  fetchTicket,
  runCsLoop,
  useTickets,
  type Ticket,
} from "@/lib/ecom-api";

const LANES = [
  { key: "new", label: "New" },
  { key: "auto_handling", label: "Auto-handling" },
  { key: "awaiting_customer", label: "Awaiting customer" },
  { key: "needs_rep", label: "Needs rep" },
  { key: "resolved", label: "Resolved" },
] as const;

const TABS = ["Tickets", "Overview", "Setup"] as const;

export default function CustomerServicePage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Tickets");
  const qc = useQueryClient();
  const tickets = useTickets();
  const [openId, setOpenId] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: runCsLoop,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ecom", "tickets"] }),
  });

  const all = tickets.data ?? [];
  const counts = {
    resolved: all.filter((t) => t.status === "resolved").length,
    needs_rep: all.filter((t) => t.status === "needs_rep").length,
    open: all.filter((t) => !["resolved"].includes(t.status)).length,
  };

  return (
    <div>
      <PageHeader
        title="Customer Service"
        subtitle="Tickets, escalation, approvals"
        actions={
          <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
            {run.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Run CS loop
          </Button>
        }
      />

      <div className="mb-4 flex gap-1 rounded-lg bg-[color:var(--surface-muted)] p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "relative rounded-md px-3 py-1.5 font-medium transition-colors",
              tab === t ? "text-strong" : "text-muted hover:text-strong",
            )}
          >
            {tab === t ? (
              <motion.span
                layoutId="cs-tab"
                transition={spring.default}
                className="absolute inset-0 rounded-md bg-[color:var(--surface)] shadow-sm"
              />
            ) : null}
            <span className="relative z-10">{t}</span>
          </button>
        ))}
      </div>

      {tab === "Tickets" ? (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {LANES.map((lane) => {
            const items = all.filter((t) => t.status === lane.key);
            return (
              <div key={lane.key} className="w-[260px] shrink-0">
                <div className="mb-2 flex items-center justify-between px-1">
                  <span className="text-[13px] font-semibold text-strong">{lane.label}</span>
                  <span className="rounded-full bg-[color:var(--surface-muted)] px-2 text-xs text-muted">
                    {items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  <AnimatePresence>
                    {items.map((t) => (
                      <TicketCard key={t.id} ticket={t} onOpen={() => setOpenId(t.id)} />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {tab === "Overview" ? (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Open tickets", value: counts.open },
            { label: "Auto-resolved", value: counts.resolved },
            { label: "Needs a rep", value: counts.needs_rep },
          ].map((c) => (
            <div
              key={c.label}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
            >
              <p className="text-[13px] text-muted">{c.label}</p>
              <p className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-strong tabular-nums">
                {c.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {tab === "Setup" ? (
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 shadow-card">
          <div className="flex items-center gap-2 text-sm font-medium text-strong">
            <ShieldCheck className="h-4 w-4 text-[color:var(--accent)]" />
            CS agent capability
          </div>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>Scope: read order data + create discounts. No refund tool (Invariant 2).</li>
            <li>Sticky escalation: once a rep is needed, replies never re-trigger auto (Invariant 3).</li>
            <li>Customer text is treated as untrusted data, never instructions (Invariant 4).</li>
            <li>SLA, tone, response prompt, and handoff rules: per-agent config (extends here).</li>
          </ul>
        </div>
      ) : null}

      <AnimatePresence>
        {openId ? <TicketDrawer id={openId} onClose={() => setOpenId(null)} /> : null}
      </AnimatePresence>
    </div>
  );
}

function TicketCard({ ticket, onOpen }: { ticket: Ticket; onOpen: () => void }) {
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: duration.base, ease: easing.standard }}
      whileHover={{ y: -2 }}
      onClick={onOpen}
      className="w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-3 text-left shadow-card"
    >
      <p className="truncate text-sm font-medium text-strong">{ticket.subject}</p>
      <p className="mt-1 truncate text-xs text-quiet">{ticket.customer_email}</p>
    </motion.button>
  );
}

function TicketDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  const ticket = useQuery({ queryKey: ["ecom", "ticket", id], queryFn: () => fetchTicket(id) });
  const d = ticket.data;
  return (
    <>
      <motion.div
        className="fixed inset-0 z-40 bg-slate-950/30 backdrop-blur-[1px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <motion.aside
        className="fixed inset-y-0 right-0 z-50 w-full max-w-[460px] overflow-y-auto border-l border-[color:var(--border)] bg-[color:var(--surface)] p-5 shadow-overlay"
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={spring.gentle}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-lg font-semibold tracking-[-0.01em] text-strong">
              {d?.subject ?? "…"}
            </p>
            <p className="mt-0.5 text-sm text-quiet">{d?.customer_email}</p>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-quiet hover:bg-[color:var(--surface-muted)]">
            <X className="h-5 w-5" />
          </button>
        </div>

        {d ? (
          <span
            className={cn(
              "mt-3 inline-block rounded-full px-2.5 py-1 text-xs font-medium capitalize",
              d.status === "resolved"
                ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
                : d.status === "needs_rep"
                  ? "bg-[color:var(--warning)]/10 text-[color:var(--warning)]"
                  : "bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
            )}
          >
            {d.status.replace("_", " ")}
          </span>
        ) : null}

        {d && d.evidence.length > 0 ? (
          <div className="mt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-quiet">
              How it was handled
            </p>
            <div className="space-y-1.5">
              {d.evidence.map((e, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-muted">
                  <span className="rounded bg-[color:var(--surface-muted)] px-1.5 py-0.5 text-[11px] font-medium text-strong">
                    {e.kind.replace("_", " ")}
                  </span>
                  <span className="truncate">{e.summary}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-5 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-quiet">
            Message history
          </p>
          {(d?.messages ?? []).map((m, i) => (
            <div
              key={i}
              className={cn(
                "rounded-lg border p-3",
                m.direction === "inbound"
                  ? "border-[color:var(--border)] bg-[color:var(--surface-muted)]"
                  : "border-[color:var(--accent-soft)] bg-[color:var(--accent-soft)]",
              )}
            >
              <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted">
                {m.direction === "inbound" ? (
                  <>
                    <User className="h-3.5 w-3.5" /> Customer
                    {m.untrusted ? (
                      <span className="rounded bg-[color:var(--surface)] px-1 text-[10px] text-quiet">
                        untrusted
                      </span>
                    ) : null}
                  </>
                ) : (
                  <>
                    <Bot className="h-3.5 w-3.5" /> CS agent
                  </>
                )}
              </div>
              <p className="whitespace-pre-wrap text-sm text-strong">{m.body}</p>
            </div>
          ))}
        </div>
      </motion.aside>
    </>
  );
}
