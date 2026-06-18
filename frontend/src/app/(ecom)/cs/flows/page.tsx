"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  Check,
  CornerDownRight,
  GitBranch,
  Loader2,
  Mail,
  Plus,
  Receipt,
  Sparkles,
  Trash2,
  UserRound,
  Wand2,
  X,
} from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { duration, easing, spring } from "@/lib/design/tokens";
import {
  saveFlow,
  useFlows,
  type Flow,
  type FlowBranch,
  type FlowStep,
} from "@/lib/ecom-api";

// ---------------------------------------------------------------------------
// Step types. "message" is the heart of the product: an LLM-generated email.
// Legacy types (send_reply / offer_discount / lookup_order / cite_policy)
// collapse into "message" for editing — their copy lives in .message.
// ---------------------------------------------------------------------------
type StepKind = "message" | "request_refund_approval" | "resolve" | "escalate";

function kindOf(type: string): StepKind {
  if (type === "request_refund_approval") return "request_refund_approval";
  if (type === "resolve") return "resolve";
  if (type === "escalate") return "escalate";
  return "message";
}

const STEP_META: Record<
  StepKind,
  { label: string; icon: typeof Mail; tint: string; ring: string }
> = {
  message: {
    label: "Message",
    icon: Mail,
    tint: "bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
    ring: "var(--accent)",
  },
  request_refund_approval: {
    label: "Refund",
    icon: Receipt,
    tint: "bg-[color:var(--warning)]/10 text-[color:var(--warning)]",
    ring: "var(--warning)",
  },
  resolve: {
    label: "Resolve",
    icon: Check,
    tint: "bg-[color:var(--success)]/10 text-[color:var(--success)]",
    ring: "var(--success)",
  },
  escalate: {
    label: "Escalate",
    icon: UserRound,
    tint: "bg-[color:var(--danger)]/10 text-[color:var(--danger)]",
    ring: "var(--danger)",
  },
};

const inputCls =
  "h-9 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 text-sm text-strong placeholder:text-quiet focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]";

// ---------------------------------------------------------------------------
// Page — left flow list, right editor. Editor remounts on flow change via key,
// so local editing state resets cleanly (no setState-in-effect).
// ---------------------------------------------------------------------------
export default function FlowsPage() {
  const flows = useFlows();
  const [id, setId] = useState<string | null>(null);
  const selected =
    flows.data?.find((f) => f.id === id) ?? flows.data?.[0] ?? null;

  return (
    <div>
      <PageHeader
        title="Flows"
        subtitle="Visual playbooks for your CS agent. Every email below is written live from your prompt — you set the strategy, the agent does the writing."
      />

      <div className="grid gap-5 lg:grid-cols-[256px_1fr]">
        <aside className="space-y-1.5">
          <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-quiet">
            Your funnels
          </p>
          {(flows.data ?? []).map((f) => {
            const active = selected?.id === f.id;
            return (
              <button
                key={f.id}
                onClick={() => setId(f.id)}
                className={cn(
                  "group flex w-full items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all",
                  active
                    ? "border-[color:var(--accent)] bg-[color:var(--accent-soft)] shadow-card"
                    : "border-[color:var(--border)] bg-[color:var(--surface)] hover:border-[color:var(--border-strong)]",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors",
                    active
                      ? "bg-[color:var(--accent)] text-white"
                      : "bg-[color:var(--surface-muted)] text-muted group-hover:text-strong",
                  )}
                >
                  <GitBranch className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span
                    className={cn(
                      "block truncate text-sm font-medium",
                      active ? "text-[color:var(--accent)]" : "text-strong",
                    )}
                  >
                    {f.name}
                  </span>
                  <span className="block truncate text-[11px] text-quiet">
                    {(f.steps ?? []).length} step
                    {(f.steps ?? []).length === 1 ? "" : "s"}
                  </span>
                </span>
                <span
                  className={cn(
                    "h-2 w-2 shrink-0 rounded-full",
                    f.enabled
                      ? "bg-[color:var(--success)]"
                      : "bg-[color:var(--surface-strong)]",
                  )}
                  title={f.enabled ? "Live" : "Off"}
                />
              </button>
            );
          })}
          {flows.isLoading ? (
            <div className="h-14 animate-pulse rounded-xl bg-[color:var(--surface-muted)]" />
          ) : null}
        </aside>

        {selected ? (
          <FlowEditor key={selected.id} flow={selected} />
        ) : !flows.isLoading ? (
          <div className="rounded-xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface)] p-10 text-center text-sm text-quiet">
            No flows yet.
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FlowEditor — header (name, enabled, triggers) + the vertical funnel.
// ---------------------------------------------------------------------------
function FlowEditor({ flow }: { flow: Flow }) {
  const qc = useQueryClient();

  const [name, setName] = useState(flow.name);
  const [enabled, setEnabled] = useState(flow.enabled);
  const [triggers, setTriggers] = useState((flow.triggers ?? []).join(", "));
  const [escalate, setEscalate] = useState(
    (flow.escalate_keywords ?? []).join(", "),
  );
  const [steps, setSteps] = useState<FlowStep[]>(() =>
    (flow.steps ?? []).map((s, i) => ({ ...s, id: s.id || `step_${i + 1}` })),
  );
  const [dirty, setDirty] = useState(false);

  const touch = () => setDirty(true);

  const patchStep = (i: number, patch: Partial<FlowStep>) => {
    setSteps((prev) =>
      prev.map((s, j) => (j === i ? { ...s, ...patch } : s)),
    );
    touch();
  };

  const removeStep = (i: number) => {
    setSteps((prev) => prev.filter((_, j) => j !== i));
    touch();
  };

  const addStep = () => {
    setSteps((prev) => {
      const used = new Set(prev.map((s) => s.id));
      let n = prev.length + 1;
      let nid = `step_${n}`;
      while (used.has(nid)) nid = `step_${++n}`;
      return [
        ...prev,
        {
          id: nid,
          type: "message",
          prompt: "",
          goto: "next",
        },
      ];
    });
    touch();
  };

  // Targets a branch / goto select can point at: sibling steps + specials.
  const targets = useMemo(
    () =>
      steps
        .map((s, i) => ({ id: s.id || `step_${i + 1}`, label: s.id || `step_${i + 1}` }))
        .filter(Boolean),
    [steps],
  );

  const save = useMutation({
    mutationFn: () =>
      saveFlow(flow.id, {
        name,
        enabled,
        triggers: splitList(triggers),
        escalate_keywords: splitList(escalate),
        steps,
      }),
    onSuccess: () => {
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["ecom", "flows"] });
    },
  });

  return (
    <div className="space-y-4">
      {/* Helper banner — the core promise of the product. */}
      <div className="flex items-start gap-2.5 rounded-xl border border-[color:var(--accent-soft)] bg-[color:var(--accent-soft)] p-3.5 text-[color:var(--accent)]">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
        <p className="text-xs leading-relaxed">
          The agent writes <span className="font-semibold">every email</span>{" "}
          from these prompts — no canned text. Describe the intent and the offer;
          it handles the wording, then classifies the reply to pick the next
          branch.
        </p>
      </div>

      {/* Header card — name + enabled toggle. */}
      <div className="flex items-center justify-between gap-4 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
        <input
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            touch();
          }}
          className="min-w-0 flex-1 bg-transparent text-lg font-semibold tracking-[-0.01em] text-strong outline-none"
        />
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-medium text-muted">
            {enabled ? "Live" : "Off"}
          </span>
          <button
            type="button"
            onClick={() => {
              setEnabled((v) => !v);
              touch();
            }}
            className={cn(
              "relative h-6 w-11 rounded-full transition-colors",
              enabled
                ? "bg-[color:var(--accent)]"
                : "bg-[color:var(--surface-strong)]",
            )}
            aria-label="Toggle enabled"
          >
            <motion.span
              layout
              transition={spring.snappy}
              className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm"
              style={{ left: enabled ? 22 : 2 }}
            />
          </button>
        </div>
      </div>

      {/* Triggers + escalate keywords. */}
      <div className="grid gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card sm:grid-cols-2">
        <ChipField
          label="Starts this flow when the email mentions"
          value={triggers}
          onChange={(v) => {
            setTriggers(v);
            touch();
          }}
          placeholder="refund, return, cancel"
        />
        <ChipField
          label="Skip straight to a human if it mentions"
          value={escalate}
          onChange={(v) => {
            setEscalate(v);
            touch();
          }}
          placeholder="lawyer, chargeback, fraud"
        />
      </div>

      {/* The funnel. */}
      <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-muted)]/40 p-5">
        <div className="flex flex-col items-center">
          <StartNode />
          <AnimatePresence initial={false}>
            {steps.map((step, i) => (
              <StepNode
                key={step.id || i}
                index={i}
                step={step}
                targets={targets}
                onPatch={(patch) => patchStep(i, patch)}
                onRemove={() => removeStep(i)}
              />
            ))}
          </AnimatePresence>

          <Connector />
          <button
            type="button"
            onClick={addStep}
            className="flex items-center gap-2 rounded-xl border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface)] px-4 py-2.5 text-sm font-medium text-muted transition-all hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
          >
            <Plus className="h-4 w-4" />
            Add step
          </button>
        </div>
      </div>

      {/* Save bar. */}
      <div className="sticky bottom-4 z-10 flex items-center justify-between gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/90 p-3 shadow-card backdrop-blur">
        <span className="flex items-center gap-2 pl-1 text-xs text-quiet">
          {dirty ? (
            <>
              <span className="h-2 w-2 rounded-full bg-[color:var(--warning)]" />
              Unsaved changes
            </>
          ) : save.isSuccess ? (
            <>
              <Check className="h-3.5 w-3.5 text-[color:var(--success)]" />
              All changes saved
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-[color:var(--surface-strong)]" />
              Up to date
            </>
          )}
        </span>
        <Button
          size="sm"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : !dirty && save.isSuccess ? (
            <Check className="h-4 w-4" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          Save flow
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Funnel pieces.
// ---------------------------------------------------------------------------
function Connector({ tall = false }: { tall?: boolean }) {
  return (
    <div
      className={cn(
        "w-px bg-[color:var(--border-strong)]",
        tall ? "h-6" : "h-4",
      )}
    />
  );
}

function StartNode() {
  return (
    <div className="flex items-center gap-2 rounded-full border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-1.5 text-xs font-medium text-muted shadow-card">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[color:var(--accent)] opacity-50" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-[color:var(--accent)]" />
      </span>
      Ticket enters the flow
    </div>
  );
}

function StepNode({
  index,
  step,
  targets,
  onPatch,
  onRemove,
}: {
  index: number;
  step: FlowStep;
  targets: { id: string; label: string }[];
  onPatch: (patch: Partial<FlowStep>) => void;
  onRemove: () => void;
}) {
  const kind = kindOf(step.type);
  const meta = STEP_META[kind];
  const Icon = meta.icon;
  const isMessage = kind === "message";

  // Legacy copy lives in .message — surface it as the prompt if prompt is empty.
  const promptValue = step.prompt ?? (isMessage ? step.message ?? "" : "");

  const branches = step.branches ?? [];
  const hasBranches = branches.length > 0;

  const setBranch = (bi: number, patch: Partial<FlowBranch>) =>
    onPatch({
      branches: branches.map((b, j) => (j === bi ? { ...b, ...patch } : b)),
    });

  const addBranch = () => {
    const fallthrough =
      targets.find((t) => t.id !== step.id)?.id ?? "resolve";
    // Seed the first conversion to branching with the canonical satisfied/not pair.
    const next: FlowBranch[] =
      branches.length === 0
        ? [
            { label: "is satisfied / accepts", goto: "resolve" },
            { label: "is not satisfied / declines", goto: fallthrough },
          ]
        : [...branches, { label: "", goto: fallthrough }];
    onPatch({ branches: next, goto: undefined });
  };

  const removeBranch = (bi: number) =>
    onPatch({ branches: branches.filter((_, j) => j !== bi) });

  const siblingTargets = targets.filter((t) => t.id !== step.id);

  return (
    <>
      <Connector tall />
      <motion.div
        layout
        initial={{ opacity: 0, y: 12, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: duration.base, ease: easing.standard }}
        className="w-full max-w-xl overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card"
        style={{ borderTopColor: meta.ring, borderTopWidth: 2 }}
      >
        {/* Card header. */}
        <div className="flex items-center gap-2.5 border-b border-[color:var(--border)] px-4 py-2.5">
          <span
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-lg",
              meta.tint,
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </span>
          <span className="flex items-center gap-2">
            <span className="text-sm font-semibold text-strong">
              {meta.label}
            </span>
            <span className="text-[11px] text-quiet">·</span>
            <input
              value={step.id ?? ""}
              onChange={(e) => onPatch({ id: slugifyId(e.target.value) })}
              className="w-28 rounded-md bg-[color:var(--surface-muted)] px-1.5 py-0.5 font-mono text-[11px] text-muted outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]"
              aria-label="Step id"
            />
          </span>
          <span className="ml-auto text-[11px] font-medium text-quiet">
            #{index + 1}
          </span>
          <button
            type="button"
            onClick={onRemove}
            className="rounded-md p-1 text-quiet transition-colors hover:bg-[color:var(--danger)]/10 hover:text-[color:var(--danger)]"
            aria-label="Delete step"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Card body. */}
        <div className="space-y-3 p-4">
          {isMessage ? (
            <>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted">
                  What should the agent write here?
                </label>
                <textarea
                  value={promptValue}
                  onChange={(e) => onPatch({ prompt: e.target.value })}
                  placeholder="Apologize warmly, offer 50% off THIS order to keep it, and mention the coupon code in the email."
                  className="h-24 w-full resize-none rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-2.5 text-sm leading-relaxed text-strong placeholder:text-quiet focus-visible:border-[color:var(--accent)] focus-visible:outline-none"
                />
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-muted">
                  Coupon with this email
                </label>
                <div className="flex items-center">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={step.discount_percent ?? 0}
                    onChange={(e) =>
                      onPatch({
                        discount_percent: clamp(Number(e.target.value), 0, 100),
                      })
                    }
                    className="h-8 w-16 rounded-l-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-2 text-sm text-strong outline-none focus-visible:border-[color:var(--accent)]"
                  />
                  <span className="flex h-8 items-center rounded-r-lg border border-l-0 border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-quiet">
                    %
                  </span>
                </div>
                {!step.discount_percent ? (
                  <span className="text-[11px] text-quiet">no coupon</span>
                ) : null}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted">
              {kind === "request_refund_approval"
                ? "Files a refund for human approval — the agent never refunds on its own."
                : kind === "resolve"
                  ? "Closes the ticket as resolved."
                  : "Hands the ticket to a human rep."}
            </p>
          )}

          {/* Routing — only message steps branch / advance. */}
          {isMessage ? (
            <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)]/50 p-3">
              {hasBranches ? (
                <>
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-strong">
                    <GitBranch className="h-3.5 w-3.5 text-[color:var(--accent)]" />
                    Wait for the reply, then route on it
                  </p>
                  <div className="space-y-2">
                    {branches.map((b, bi) => (
                      <BranchRow
                        key={bi}
                        branch={b}
                        targets={siblingTargets}
                        onChange={(patch) => setBranch(bi, patch)}
                        onRemove={() => removeBranch(bi)}
                      />
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={addBranch}
                    className="mt-2 flex items-center gap-1.5 text-xs font-medium text-[color:var(--accent)] hover:underline"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add branch
                  </button>
                </>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex items-center gap-1.5 text-xs font-medium text-muted">
                    <ArrowDown className="h-3.5 w-3.5" />
                    Then go to
                  </span>
                  <GotoSelect
                    value={step.goto ?? "next"}
                    targets={siblingTargets}
                    allowNext
                    onChange={(v) => onPatch({ goto: v })}
                  />
                  <button
                    type="button"
                    onClick={addBranch}
                    className="ml-auto flex items-center gap-1.5 text-xs font-medium text-[color:var(--accent)] hover:underline"
                  >
                    <GitBranch className="h-3.5 w-3.5" />
                    Wait &amp; branch instead
                  </button>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </motion.div>

      {/* Outgoing routing visualised below the card. */}
      {isMessage && hasBranches ? (
        <BranchArrows branches={branches} targets={targets} stepId={step.id} />
      ) : null}
    </>
  );
}

function BranchRow({
  branch,
  targets,
  onChange,
  onRemove,
}: {
  branch: FlowBranch;
  targets: { id: string; label: string }[];
  onChange: (patch: Partial<FlowBranch>) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-quiet">when the customer</span>
      <input
        value={branch.label}
        onChange={(e) => onChange({ label: e.target.value })}
        placeholder="is satisfied / accepts"
        className={cn(inputCls, "h-8 flex-1 min-w-[8rem] text-xs")}
      />
      <CornerDownRight className="h-3.5 w-3.5 shrink-0 text-quiet" />
      <GotoSelect
        value={branch.goto}
        targets={targets}
        onChange={(v) => onChange({ goto: v })}
      />
      <button
        type="button"
        onClick={onRemove}
        className="rounded-md p-1 text-quiet hover:bg-[color:var(--danger)]/10 hover:text-[color:var(--danger)]"
        aria-label="Remove branch"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function GotoSelect({
  value,
  targets,
  allowNext = false,
  onChange,
}: {
  value: string;
  targets: { id: string; label: string }[];
  allowNext?: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-8 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-2 text-xs font-medium text-strong outline-none focus-visible:border-[color:var(--accent)]"
    >
      {allowNext ? <option value="next">Continue to next step</option> : null}
      {targets.map((t) => (
        <option key={t.id} value={t.id}>
          Go to {t.label}
        </option>
      ))}
      <option value="resolve">Resolve (close)</option>
      <option value="escalate">Escalate to human</option>
    </select>
  );
}

/** The labelled arrows beneath a branching step — the visual heart of the funnel. */
function BranchArrows({
  branches,
  targets,
  stepId,
}: {
  branches: FlowBranch[];
  targets: { id: string; label: string }[];
  stepId?: string;
}) {
  const labelFor = (goto: string) => {
    if (goto === "resolve") return "Resolve";
    if (goto === "escalate") return "Escalate";
    const t = targets.find((x) => x.id === goto);
    return t ? t.label : goto;
  };
  const tint = (goto: string) =>
    goto === "resolve"
      ? "border-[color:var(--success)]/30 bg-[color:var(--success)]/5 text-[color:var(--success)]"
      : goto === "escalate"
        ? "border-[color:var(--danger)]/30 bg-[color:var(--danger)]/5 text-[color:var(--danger)]"
        : "border-[color:var(--accent-soft)] bg-[color:var(--accent-soft)] text-[color:var(--accent)]";

  return (
    <>
      <Connector />
      <div className="flex w-full max-w-xl flex-wrap items-stretch justify-center gap-2">
        {branches.map((b, i) => (
          <div
            key={`${stepId}-${i}`}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
              tint(b.goto),
            )}
          >
            <span className="text-quiet">if</span>
            <span className="max-w-[10rem] truncate">
              {b.label || "…"}
            </span>
            <ArrowDown className="h-3 w-3 -rotate-90" />
            <span className="font-semibold">{labelFor(b.goto)}</span>
          </div>
        ))}
      </div>
    </>
  );
}

/** Comma-list input that renders its current values as live chips. */
function ChipField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const chips = splitList(value);
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputCls}
      />
      {chips.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {chips.map((c, i) => (
            <span
              key={`${c}-${i}`}
              className="rounded-full bg-[color:var(--surface-muted)] px-2 py-0.5 text-[11px] font-medium text-muted"
            >
              {c}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function splitList(s: string): string[] {
  return s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.max(lo, Math.min(hi, n));
}

function slugifyId(s: string): string {
  return s.replace(/[^a-zA-Z0-9_-]/g, "_");
}
