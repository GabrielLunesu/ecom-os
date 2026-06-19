"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { CircleSlash, LockKeyhole, RefreshCcw } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { useMetricSnapshot } from "@/lib/ecom-api";
import {
  FailurePanel,
  LoadingBlock,
  MetricSection,
  StatusCue,
  querySurface,
  surfaceCopy,
} from "../../finance-ui";

function readParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : (value ?? null);
}

export default function MetricSnapshotDetailPage() {
  const params = useParams<{ snapshotId?: string | string[] }>();
  const snapshotId = readParam(params.snapshotId);
  const snapshot = useMetricSnapshot(snapshotId);
  const state = querySurface(snapshot);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Metric Detail"
        subtitle={snapshotId ? `Snapshot ${snapshotId}` : "Missing snapshot id"}
        actions={
          <Link
            href="/finance"
            className="inline-flex min-h-9 items-center rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
          >
            Finance
          </Link>
        }
      />

      {!snapshotId ? (
        <FailurePanel
          icon={CircleSlash}
          title="Missing metric snapshot id"
          detail="A metric drilldown must name the exact snapshot. No latest/default snapshot is inferred."
        />
      ) : null}

      {snapshotId ? (
        <div className="grid gap-3 md:grid-cols-3">
          <StatusCue
            state={state}
            label="Snapshot read"
            detail={surfaceCopy(state, "snapshot")}
          />
          <StatusCue
            state={snapshot.data?.coverage.status ?? state}
            label="Coverage"
            detail={
              snapshot.data
                ? `${snapshot.data.coverage.percent}% · ${snapshot.data.coverage.freshness}`
                : "Awaiting snapshot data."
            }
          />
          <StatusCue
            state={snapshot.data?.calculation_status ?? state}
            label="Calculation"
            detail={
              snapshot.data?.trace_id
                ? `Trace ${snapshot.data.trace_id}`
                : "Trace pending."
            }
          />
        </div>
      ) : null}

      {state === "loading" ? <LoadingBlock label="Metric detail" /> : null}
      {snapshotId && state !== "loading" && snapshot.data ? (
        <div className="space-y-4">
          <MetricSection snapshot={snapshot.data} />
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
            <p className="text-sm font-semibold text-strong">
              Narration guardrails
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted">
              <li>Do not recalculate or alter metric values.</li>
              <li>
                Use component evidence and warnings as the source for
                explanation.
              </li>
              <li>
                Call the metric estimated contribution margin, not audited
                profit.
              </li>
            </ul>
          </div>
        </div>
      ) : null}
      {snapshotId && state !== "loading" && !snapshot.data ? (
        <FailurePanel
          icon={
            state === "permission"
              ? LockKeyhole
              : state === "empty"
                ? CircleSlash
                : RefreshCcw
          }
          title={surfaceCopy(state, "metric snapshot")}
          detail="The detail route reads one persisted A08 snapshot by id and does not fall back to legacy metrics or latest/default account selection."
        />
      ) : null}
    </div>
  );
}
