"use client";

import { Sparkles } from "lucide-react";

/** Prompt library — the per-step instructions the CS agent uses to GENERATE each
 * email. Every reply is LLM-generated from these prompts + the order context, never
 * a fixed template. Editing happens inline on each flow step (CS → Flows); this page
 * is the consolidated view across flows. Filled in once flow-v2 lands. */
export default function CsPromptsPage() {
  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[color:var(--accent)]" />
        <h1 className="text-xl font-semibold tracking-[-0.02em] text-strong">Prompts</h1>
      </div>
      <p className="mb-6 text-sm text-muted">
        The instructions your agent uses to write each email. Every reply is generated
        from a prompt + the real order context — never a fixed template.
      </p>
      <div className="rounded-xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface)] p-8 text-center">
        <p className="text-sm text-muted">
          Prompts are edited per step inside each flow. Open{" "}
          <span className="font-medium text-strong">CS → Flows</span> to write the prompt
          for each step of a funnel. This page will list every prompt across your flows.
        </p>
      </div>
    </div>
  );
}
