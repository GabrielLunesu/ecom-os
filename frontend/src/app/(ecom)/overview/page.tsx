"use client";

import Link from "next/link";
import { AlertCircle, ArrowRight, RefreshCw, Search } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  todayFreshnessLabel,
  todaySourceHref,
  todayTraceHref,
  todayUnavailableDependencies,
  useTodayAttention,
} from "@/lib/ecom-api";

const severityClass: Record<string, string> = {
  critical: "border-[color:var(--danger)] text-[color:var(--danger)]",
  high: "border-[color:var(--danger)] text-[color:var(--danger)]",
  medium: "border-[color:var(--warning)] text-[color:var(--warning)]",
  low: "border-[color:var(--border-strong)] text-muted",
  info: "border-[color:var(--border-strong)] text-muted",
};

const formatSnapshotTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(value))
    : "not set";

export default function OverviewPage() {
  const attention = useTodayAttention();
  const snapshot = attention.data;
  const items = snapshot?.items ?? [];

  return (
    <div>
      <PageHeader
        title="Today"
        subtitle="Deterministic attention queue with source state and ranking reasons"
        actions={
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => attention.refetch()}
            disabled={attention.isFetching}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {attention.isLoading ? (
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          Loading attention queue…
        </div>
      ) : attention.isError ? (
        <div className="rounded-lg border border-[color:var(--danger)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          <div className="flex items-center gap-2 font-medium text-[color:var(--danger)]">
            <AlertCircle className="h-4 w-4" />
            Today is unavailable
          </div>
          <p className="mt-2">
            Attention inputs are not treated as clear or zero while ranking is
            unavailable.
          </p>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          No attention items are currently available.
        </div>
      ) : (
        <div className="space-y-3">
          {snapshot ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3 text-xs text-muted shadow-card">
              <span className="font-medium text-strong">
                Snapshot {snapshot.id}
              </span>
              <span>{snapshot.status}</span>
              <span>{snapshot.source_status}</span>
              <span>
                {snapshot.item_count} ranked from {snapshot.input_count} inputs
              </span>
              <span>
                Window {formatSnapshotTime(snapshot.window_start)} to{" "}
                {formatSnapshotTime(snapshot.window_end)}
              </span>
            </div>
          ) : null}
          {items.map((item) => {
            const unavailableDependencies = todayUnavailableDependencies(item);
            const freshnessLabel = todayFreshnessLabel(item.freshness_as_of);

            return (
              <article
                key={`${item.kind}:${item.id}`}
                className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold tabular-nums text-muted">
                        #{item.rank}
                      </span>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-[11px] font-medium",
                          severityClass[item.severity],
                        )}
                      >
                        {item.severity}
                      </span>
                      <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                        {item.source_status}
                      </span>
                      <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                        {item.coverage}
                      </span>
                      <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] tabular-nums text-muted">
                        score {item.score}
                      </span>
                      {freshnessLabel ? (
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                          fresh {freshnessLabel}
                        </span>
                      ) : null}
                    </div>
                    <h2 className="mt-2 text-base font-semibold text-strong">
                      {item.title}
                    </h2>
                    {item.summary ? (
                      <p className="mt-1 text-sm text-muted">{item.summary}</p>
                    ) : null}
                  </div>

                  {item.primary_action ? (
                    <Link
                      href={item.primary_action}
                      className="inline-flex h-9 items-center gap-2 rounded-lg border border-[color:var(--border)] px-3 text-sm font-medium text-strong hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
                    >
                      Open
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  ) : null}
                </div>

                {unavailableDependencies.length > 0 ? (
                  <div className="mt-3 rounded-md border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 py-2">
                    <p className="text-xs font-semibold text-muted">
                      Unavailable inputs
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {unavailableDependencies.map((dependency) => (
                        <span
                          key={dependency}
                          className="rounded bg-[color:var(--surface)] px-2 py-1 text-xs text-muted"
                        >
                          {dependency}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold text-muted">
                      Ranking reasons
                    </p>
                    <ul className="mt-1 space-y-1">
                      {item.reasons.map((reason) => (
                        <li key={reason} className="text-xs text-quiet">
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-muted">Sources</p>
                    {item.source_refs?.length ? (
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {item.source_refs.map((source) => {
                          const href = todaySourceHref(
                            source,
                            item.primary_action,
                          );
                          const label = `${source.type}: ${source.label || source.id}`;
                          return href ? (
                            <Link
                              key={`${source.type}:${source.id}`}
                              href={href}
                              className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-xs text-muted hover:text-[color:var(--accent)]"
                            >
                              {label}
                            </Link>
                          ) : (
                            <span
                              key={`${source.type}:${source.id}`}
                              className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-xs text-muted"
                            >
                              {label}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="mt-1 text-xs text-quiet">
                        No source link accepted yet.
                      </p>
                    )}
                    {item.trace_id ? (
                      <p className="mt-2 text-xs text-quiet">
                        {todayTraceHref(item.trace_id) ? (
                          <Link
                            href={todayTraceHref(item.trace_id) as string}
                            className="hover:text-[color:var(--accent)]"
                          >
                            Trace {item.trace_id}
                          </Link>
                        ) : (
                          <>Trace {item.trace_id}</>
                        )}
                      </p>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2 text-xs text-quiet">
        <Search className="h-3.5 w-3.5" />
        Missing upstream inputs appear as unavailable attention items, not zero
        counts.
      </div>
    </div>
  );
}
