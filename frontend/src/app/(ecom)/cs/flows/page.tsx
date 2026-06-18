"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Check, GitBranch, Loader2, ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { saveFlow, useFlows, type Flow, type FlowStep } from "@/lib/ecom-api";

const STEP_LABELS: Record<string, string> = {
  lookup_order: "Look up the customer's order",
  cite_policy: "Cite a brand policy",
  send_reply: "Send a reply",
  offer_discount: "Offer a discount (deflect)",
  request_refund_approval: "File a refund for human approval",
  escalate: "Escalate to a rep",
  resolve: "Close the ticket",
};

export default function FlowsPage() {
  const flows = useFlows();
  const [id, setId] = useState<string | null>(null);
  const selected = flows.data?.find((f) => f.id === id) ?? flows.data?.[0] ?? null;

  useEffect(() => {
    if (!id && flows.data && flows.data.length) setId(flows.data[0].id);
  }, [id, flows.data]);

  return (
    <div>
      <PageHeader
        title="Flows"
        subtitle="Your CS playbook — classify a ticket, run a flow. Edit the wording and tiers; the logic stays safe."
      />
      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <div className="space-y-1">
          {(flows.data ?? []).map((f) => (
            <button
              key={f.id}
              onClick={() => setId(f.id)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                selected?.id === f.id
                  ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                  : "text-muted hover:bg-[color:var(--surface-muted)]",
              )}
            >
              <GitBranch className="h-4 w-4 shrink-0" />
              <span className="flex-1 truncate">{f.name}</span>
              {!f.enabled ? <span className="text-[10px] text-quiet">off</span> : null}
            </button>
          ))}
        </div>
        {selected ? <FlowEditor key={selected.id} flow={selected} /> : null}
      </div>
    </div>
  );
}

function FlowEditor({ flow }: { flow: Flow }) {
  const qc = useQueryClient();
  const [name, setName] = useState(flow.name);
  const [enabled, setEnabled] = useState(flow.enabled);
  const [triggers, setTriggers] = useState((flow.triggers ?? []).join(", "));
  const [escalate, setEscalate] = useState((flow.escalate_keywords ?? []).join(", "));
  const [steps, setSteps] = useState<FlowStep[]>(flow.steps ?? []);

  useEffect(() => {
    setName(flow.name);
    setEnabled(flow.enabled);
    setTriggers((flow.triggers ?? []).join(", "));
    setEscalate((flow.escalate_keywords ?? []).join(", "));
    setSteps(flow.steps ?? []);
  }, [flow]);

  const patchStep = (i: number, patch: Partial<FlowStep>) =>
    setSteps((s) => s.map((step, j) => (j === i ? { ...step, ...patch } : step)));

  const save = useMutation({
    mutationFn: () =>
      saveFlow(flow.id, {
        name,
        enabled,
        triggers: triggers.split(",").map((t) => t.trim()).filter(Boolean),
        escalate_keywords: escalate.split(",").map((t) => t.trim()).filter(Boolean),
        steps,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ecom", "flows"] }),
  });

  const field =
    "w-full rounded-lg bg-[color:var(--surface-muted)] p-2.5 text-sm text-strong outline-none";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="bg-transparent text-lg font-semibold tracking-[-0.01em] text-strong outline-none"
        />
        <button
          onClick={() => setEnabled((v) => !v)}
          className={cn(
            "relative h-6 w-11 rounded-full transition-colors",
            enabled ? "bg-[color:var(--accent)]" : "bg-[color:var(--surface-strong)]",
          )}
        >
          <motion.span
            layout
            className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm"
            style={{ left: enabled ? 22 : 2 }}
          />
        </button>
      </div>

      <div className="grid gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-muted">Trigger phrases (comma-separated)</label>
          <input value={triggers} onChange={(e) => setTriggers(e.target.value)} className={`mt-1 ${field}`} />
        </div>
        <div>
          <label className="text-xs font-medium text-muted">Escalate immediately on (comma-separated)</label>
          <input value={escalate} onChange={(e) => setEscalate(e.target.value)} className={`mt-1 ${field}`} />
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step, i) => (
          <div
            key={i}
            className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--accent-soft)] text-[11px] font-semibold text-[color:var(--accent)]">
                {i + 1}
              </span>
              <span className="text-sm font-medium text-strong">
                {STEP_LABELS[step.type] ?? step.type}
              </span>
            </div>
            {step.type === "offer_discount" ? (
              <div className="mt-2 flex items-center gap-2">
                <label className="text-xs text-muted">Discount %</label>
                <input
                  type="number"
                  min={0}
                  max={20}
                  value={step.percent ?? 0}
                  onChange={(e) => patchStep(i, { percent: Math.min(20, Number(e.target.value)) })}
                  className="w-20 rounded-lg bg-[color:var(--surface-muted)] p-1.5 text-sm text-strong outline-none"
                />
                <span className="text-[11px] text-quiet">capped at 20%</span>
              </div>
            ) : null}
            {step.type === "cite_policy" ? (
              <input
                value={step.slug ?? ""}
                onChange={(e) => patchStep(i, { slug: e.target.value })}
                placeholder="vault slug (e.g. shipping-policy)"
                className={`mt-2 ${field}`}
              />
            ) : null}
            {"message" in step || ["send_reply", "offer_discount", "request_refund_approval"].includes(step.type) ? (
              <textarea
                value={step.message ?? ""}
                onChange={(e) => patchStep(i, { message: e.target.value })}
                placeholder="Customer-facing message (use {customer_name}, {order_name}, {tracking_url}, {discount_code}, {policy_excerpt})"
                className={`mt-2 h-24 resize-none ${field}`}
              />
            ) : null}
            {step.type === "offer_discount" ? (
              <textarea
                value={step.accept_message ?? ""}
                onChange={(e) => patchStep(i, { accept_message: e.target.value })}
                placeholder="Message when the customer accepts the offer"
                className={`mt-2 h-16 resize-none ${field}`}
              />
            ) : null}
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 rounded-xl bg-[color:var(--accent-soft)] p-3 text-xs text-[color:var(--accent)]">
        <ShieldCheck className="h-4 w-4 shrink-0" />
        Safe by design: discounts are capped at 20% and the refund step only files an approval —
        a flow can never issue a refund on its own (Invariant 2).
      </div>

      <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : save.isSuccess ? (
          <Check className="h-4 w-4" />
        ) : null}
        Save flow
      </Button>
    </div>
  );
}
