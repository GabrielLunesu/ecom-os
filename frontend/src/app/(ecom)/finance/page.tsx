"use client";

import Link from "next/link";
import { CircleSlash, LockKeyhole, RefreshCcw, Route } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { ALL_STORES, useStore } from "@/components/ecom/store-context";
import {
  DailyBriefSection,
  FailurePanel,
  LoadingBlock,
  MetricSection,
  StatusCue,
  querySurface,
  surfaceCopy,
} from "./finance-ui";
import { useLatestDailyBrief, useLatestMetricSnapshot } from "@/lib/ecom-api";

function DetailLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex min-h-9 items-center rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
    >
      {label}
    </Link>
  );
}

export default function FinancePage() {
  const { activeStore, activeStoreId, isAggregate } = useStore();
  const exactStoreId = activeStoreId === ALL_STORES ? null : activeStoreId;
  const metric = useLatestMetricSnapshot(exactStoreId);
  const brief = useLatestDailyBrief(exactStoreId);
  const metricState = querySurface(metric);
  const briefState = querySurface(brief);

  if (isAggregate) {
    return (
      <div>
        <PageHeader
          title="Finance"
          subtitle="Estimated contribution margin, evidence, and native daily brief"
        />
        <FailurePanel
          icon={LockKeyhole}
          title="Select one exact store"
          detail="Finance reads do not choose a default, latest, or aggregate account. Pick a store in the store switcher to load deterministic metrics."
        />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        title="Finance"
        subtitle={`${activeStore?.name ?? exactStoreId} · deterministic metrics and evidence`}
      />

      <div className="grid gap-3 md:grid-cols-3">
        <StatusCue
          state="ready"
          label="Exact store scope"
          detail={exactStoreId ?? "No store selected"}
        />
        <StatusCue
          state={metricState}
          label="Metric snapshot"
          detail={surfaceCopy(metricState, "metric snapshot")}
        />
        <StatusCue
          state={briefState}
          label="Daily brief"
          detail={surfaceCopy(briefState, "daily brief")}
        />
      </div>

      {metricState === "loading" ? (
        <LoadingBlock label="Metric snapshot" />
      ) : null}
      {metricState !== "loading" && metric.data ? (
        <div className="space-y-3">
          <div className="flex justify-end">
            <DetailLink
              href={`/finance/metric-snapshots/${metric.data.id}`}
              label="Open metric detail"
            />
          </div>
          <MetricSection snapshot={metric.data} />
        </div>
      ) : null}
      {metricState !== "loading" && !metric.data ? (
        <FailurePanel
          icon={
            metricState === "permission"
              ? LockKeyhole
              : metricState === "empty"
                ? CircleSlash
                : RefreshCcw
          }
          title={surfaceCopy(metricState, "metric snapshot")}
          detail="The Finance page only renders A08 snapshots with formula version, currency, timezone, coverage, and evidence. Legacy revenue/AOV metrics are not substituted."
        />
      ) : null}

      {briefState === "loading" ? <LoadingBlock label="Daily brief" /> : null}
      {briefState !== "loading" && brief.data ? (
        <div className="space-y-3">
          <div className="flex justify-end">
            <DetailLink
              href={`/finance/daily-briefs/${brief.data.id}`}
              label="Open brief detail"
            />
          </div>
          <DailyBriefSection brief={brief.data} />
        </div>
      ) : null}
      {briefState !== "loading" && !brief.data ? (
        <FailurePanel
          icon={
            briefState === "permission"
              ? LockKeyhole
              : briefState === "empty"
                ? CircleSlash
                : Route
          }
          title={surfaceCopy(briefState, "daily brief")}
          detail="A08 can show deterministic fallback text, narration state, delivery intents, outcome_unknown, and trace refs once the exported router is mounted."
        />
      ) : null}
    </div>
  );
}
