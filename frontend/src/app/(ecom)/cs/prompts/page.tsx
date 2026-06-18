"use client";

import Link from "next/link";
import { Sparkles, ArrowUpRight } from "lucide-react";

import { useFlows, type Flow } from "@/lib/ecom-api";

/** Prompt library — every per-step instruction the CS agent writes from, across all
 * flows. Each reply is LLM-generated from one of these prompts + the live order
 * context, never a fixed template. Edit them per step in CS → Flows. */
export default function CsPromptsPage() {
  const flows = useFlows();
  const list = flows.data ?? [];

  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[color:var(--accent)]" />
        <h1 className="text-xl font-semibold tracking-[-0.02em] text-strong">Prompts</h1>
      </div>
      <p className="mb-6 text-sm text-muted">
        The instructions your agent writes each email from. Every reply is generated
        from a prompt + the real order context — never a fixed template. Edit them per
        step in <Link href="/cs/flows" className="font-medium text-[color:var(--accent)]">Flows</Link>.
      </p>

      {list.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface)] p-8 text-center text-sm text-muted">
          {flows.isLoading ? "Loading…" : "No flows yet — create one in Flows."}
        </div>
      ) : (
        <div className="space-y-6">
          {list.map((flow) => (
            <FlowPrompts key={flow.id} flow={flow} />
          ))}
        </div>
      )}
    </div>
  );
}

function FlowPrompts({ flow }: { flow: Flow }) {
  const steps = (flow.steps ?? []).filter((s) => (s.prompt ?? s.message ?? "").trim());
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold tracking-[-0.01em] text-strong">
          {flow.name}
          {!flow.enabled ? (
            <span className="rounded-full bg-[color:var(--surface-muted)] px-2 py-0.5 text-[11px] font-medium text-muted">
              off
            </span>
          ) : null}
        </h2>
        <Link
          href="/cs/flows"
          className="flex items-center gap-1 text-xs font-medium text-[color:var(--accent)] hover:underline"
        >
          Edit <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      {steps.length === 0 ? (
        <p className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-3 text-xs text-quiet">
          No generated-email steps in this flow.
        </p>
      ) : (
        <div className="space-y-2">
          {steps.map((s, i) => (
            <div
              key={s.id ?? i}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <span className="rounded-md bg-[color:var(--accent-soft)] px-2 py-0.5 font-mono text-[11px] text-[color:var(--accent)]">
                  {s.id ?? `step ${i + 1}`}
                </span>
                {typeof s.discount_percent === "number" ? (
                  <span className="rounded-md bg-[color:var(--surface-muted)] px-2 py-0.5 text-[11px] font-medium text-muted">
                    {s.discount_percent}% coupon
                  </span>
                ) : null}
              </div>
              <p className="whitespace-pre-wrap text-sm text-strong">
                {s.prompt ?? s.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
