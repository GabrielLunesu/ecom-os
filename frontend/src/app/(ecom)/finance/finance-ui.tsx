"use client";

import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  CircleSlash,
  type LucideIcon,
} from "lucide-react";

import { ApiError } from "@/api/mutator";
import {
  type DailyBriefDetail,
  type MetricComponentRead,
  type MetricSnapshotDetail,
} from "@/lib/ecom-api";
import { cn } from "@/lib/utils";

export type QuerySurface = {
  isLoading: boolean;
  error: Error | null;
};

export type SurfaceState =
  | "loading"
  | "ready"
  | "empty"
  | "permission"
  | "unavailable"
  | "error";

export function querySurface(query: QuerySurface): SurfaceState {
  if (query.isLoading) return "loading";
  if (!query.error) return "ready";
  if (query.error instanceof ApiError) {
    if (query.error.status === 404) return "empty";
    if (query.error.status === 401 || query.error.status === 403)
      return "permission";
    if (query.error.status === 0 || query.error.status === 503)
      return "unavailable";
  }
  return "error";
}

export function surfaceCopy(state: SurfaceState, noun: string) {
  switch (state) {
    case "loading":
      return `Loading ${noun}`;
    case "empty":
      return `No ${noun} has been published for this exact store.`;
    case "permission":
      return `You do not have access to this ${noun}.`;
    case "unavailable":
      return `${noun} is unavailable right now.`;
    case "error":
      return `${noun} could not be read.`;
    case "ready":
      return `${noun} is available.`;
  }
}

export function formatMoney(money: { minor: number; currency: string }) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency,
  }).format(money.minor / 100);
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function StatusCue({
  state,
  label,
  detail,
}: {
  state: SurfaceState | string;
  label: string;
  detail?: string;
}) {
  const isProblem = [
    "permission",
    "unavailable",
    "error",
    "failed",
    "outcome_unknown",
  ].includes(state);
  const isWaiting = ["loading", "pending", "partial", "stale"].includes(state);
  const Icon = isProblem
    ? AlertTriangle
    : isWaiting
      ? CircleDashed
      : CheckCircle2;

  return (
    <div
      className={cn(
        "flex min-h-14 items-start gap-3 rounded-lg border p-3 text-sm",
        isProblem
          ? "border-[color:rgba(180,35,24,0.35)] bg-[color:rgba(180,35,24,0.06)]"
          : isWaiting
            ? "border-[color:rgba(180,83,9,0.35)] bg-[color:rgba(180,83,9,0.07)]"
            : "border-[color:rgba(15,118,110,0.28)] bg-[color:rgba(15,118,110,0.07)]",
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn(
          "mt-0.5 h-4 w-4 shrink-0",
          isProblem
            ? "text-[color:var(--danger)]"
            : isWaiting
              ? "text-[color:var(--warning)]"
              : "text-[color:var(--success)]",
        )}
      />
      <div>
        <p className="font-medium text-strong">{label}</p>
        {detail ? <p className="mt-0.5 text-xs text-muted">{detail}</p> : null}
      </div>
    </div>
  );
}

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
      <p className="text-sm font-medium text-strong">{label}</p>
      <div className="mt-4 space-y-3">
        <div className="h-8 w-48 animate-pulse rounded-md bg-[color:var(--surface-muted)]" />
        <div className="h-3 w-full animate-pulse rounded-md bg-[color:var(--surface-muted)]" />
        <div className="h-3 w-2/3 animate-pulse rounded-md bg-[color:var(--surface-muted)]" />
      </div>
    </div>
  );
}

export function MoneyTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
      <p className="text-sm font-medium text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-strong">{value}</p>
      <p className="mt-1 text-xs text-muted">{detail}</p>
    </div>
  );
}

export function FailurePanel({
  icon: Icon,
  title,
  detail,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-5">
      <div className="flex items-start gap-3">
        <Icon
          aria-hidden="true"
          className="mt-0.5 h-5 w-5 shrink-0 text-muted"
        />
        <div>
          <p className="font-semibold text-strong">{title}</p>
          <p className="mt-1 text-sm text-muted">{detail}</p>
        </div>
      </div>
    </div>
  );
}

export function ComponentTable({
  components,
}: {
  components: MetricComponentRead[];
}) {
  if (!components.length) {
    return (
      <StatusCue
        state="empty"
        label="No component evidence"
        detail="The metric snapshot exists, but component evidence has not been attached."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)]">
      <div className="min-w-[720px]">
        <div className="grid grid-cols-[1.2fr_1fr_1fr_1.4fr] gap-3 border-b border-[color:var(--border)] px-4 py-3 text-xs font-semibold text-muted">
          <span>Component</span>
          <span className="text-right">Amount</span>
          <span className="text-right">Contribution</span>
          <span>Evidence</span>
        </div>
        {components.map((component) => (
          <div
            key={component.id}
            className="grid grid-cols-[1.2fr_1fr_1fr_1.4fr] gap-3 border-b border-[color:var(--border)] px-4 py-3 text-sm last:border-b-0"
          >
            <div>
              <p className="font-medium text-strong">
                {titleCase(component.kind)}
              </p>
              <p className="text-xs text-muted">
                {component.coverage} · {component.freshness}
              </p>
            </div>
            <p className="text-right tabular-nums text-strong">
              {formatMoney(component.amount)}
            </p>
            <p className="text-right tabular-nums text-strong">
              {formatMoney(component.contribution)}
            </p>
            <div className="min-w-0">
              <p className="truncate text-strong">{component.source_ref}</p>
              <p className="mt-0.5 truncate text-xs text-muted">
                {component.evidence_refs.length
                  ? component.evidence_refs.join(", ")
                  : "No evidence refs"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MetricSection({
  snapshot,
}: {
  snapshot: MetricSnapshotDetail;
}) {
  const missing = snapshot.coverage.missing_component_kinds;
  const warnings = snapshot.coverage.warnings;

  return (
    <section aria-labelledby="finance-metric-heading" className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2
            id="finance-metric-heading"
            className="text-lg font-semibold text-strong"
          >
            {snapshot.display_name}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {snapshot.formula_version} · {snapshot.window.timezone} ·{" "}
            {snapshot.attribution_window_days}-day attribution
          </p>
        </div>
        <p className="text-sm text-muted">
          Finalized {formatDateTime(snapshot.finalized_at)}
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <MoneyTile
          label="Estimated contribution margin"
          value={formatMoney(snapshot.value)}
          detail={`${snapshot.value.minor} minor units · ${snapshot.value.currency}`}
        />
        <MoneyTile
          label="Coverage"
          value={`${snapshot.coverage.percent}%`}
          detail={`${snapshot.coverage.status} · ${snapshot.coverage.freshness}`}
        />
        <MoneyTile
          label="Window"
          value={snapshot.window.reporting_date}
          detail={`${formatDateTime(snapshot.window.start_utc)} to ${formatDateTime(
            snapshot.window.end_utc,
          )}`}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <StatusCue
          state={snapshot.coverage.status}
          label={`Coverage is ${snapshot.coverage.status}`}
          detail={
            missing.length
              ? `Missing: ${missing.map(titleCase).join(", ")}`
              : "All required formula components are represented."
          }
        />
        <StatusCue
          state={snapshot.coverage.freshness}
          label={`Freshness is ${snapshot.coverage.freshness}`}
          detail={`FX basis: ${snapshot.fx_basis}`}
        />
        <StatusCue
          state={snapshot.calculation_status}
          label={`Calculation is ${snapshot.calculation_status}`}
          detail={
            snapshot.trace_id
              ? `Trace ${snapshot.trace_id}`
              : "Trace pending registration."
          }
        />
      </div>

      {warnings.length ? (
        <div className="rounded-lg border border-[color:rgba(180,83,9,0.35)] bg-[color:rgba(180,83,9,0.07)] p-4">
          <p className="text-sm font-semibold text-strong">Warnings</p>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            {warnings.map((warning) => (
              <li key={warning} className="flex gap-2">
                <AlertTriangle
                  aria-hidden="true"
                  className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--warning)]"
                />
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <ComponentTable components={snapshot.components} />
    </section>
  );
}

export function DailyBriefSection({ brief }: { brief: DailyBriefDetail }) {
  const text = brief.final_text ?? brief.deterministic_fallback_text;
  const deliveryState = brief.delivery_intents.some(
    (intent) => intent.status === "outcome_unknown",
  )
    ? "outcome_unknown"
    : brief.delivery_intents.some((intent) => intent.status === "failed")
      ? "failed"
      : brief.delivery_intents.length
        ? "ready"
        : "pending";

  return (
    <section aria-labelledby="daily-brief-heading" className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2
            id="daily-brief-heading"
            className="text-lg font-semibold text-strong"
          >
            Native daily brief
          </h2>
          <p className="mt-1 text-sm text-muted">
            Revision {brief.revision} · schema {brief.schema_version} ·{" "}
            {brief.window.timezone}
          </p>
        </div>
        <p className="text-sm text-muted">
          Body hash{" "}
          <span className="font-mono">
            {brief.final_body_hash.slice(0, 12)}
          </span>
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <StatusCue
          state={brief.status}
          label={`Snapshot is ${brief.status}`}
          detail={`${brief.coverage.percent}% coverage · ${brief.coverage.freshness}`}
        />
        <StatusCue
          state={brief.narration_status}
          label={`Narration is ${brief.narration_status}`}
          detail={
            brief.narration_error ?? "Deterministic fallback remains available."
          }
        />
        <StatusCue
          state={deliveryState}
          label={`${brief.delivery_intents.length} delivery intent${brief.delivery_intents.length === 1 ? "" : "s"}`}
          detail={
            brief.delivered_at
              ? `Delivered ${formatDateTime(brief.delivered_at)}`
              : "No direct channel send is performed by this page."
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
          <p className="text-sm font-semibold text-strong">Brief body</p>
          <pre className="mt-3 max-h-80 whitespace-pre-wrap break-words rounded-md bg-[color:var(--surface-muted)] p-3 font-sans text-sm leading-6 text-muted">
            {text}
          </pre>
        </div>

        <div className="space-y-3">
          {brief.sections.map((section) => (
            <div
              key={`${section.kind}-${section.title}`}
              className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4"
            >
              <p className="text-sm font-semibold text-strong">
                {section.title}
              </p>
              <p className="mt-1 text-xs text-muted">
                {section.coverage} · {section.freshness}
              </p>
              <p className="mt-2 text-xs text-muted">
                {section.evidence_refs.length
                  ? `Evidence: ${section.evidence_refs.join(", ")}`
                  : "Evidence refs pending."}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export { CircleSlash };
