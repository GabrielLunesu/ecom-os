"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { CircleSlash, LockKeyhole, RefreshCcw } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import {
  type DailyBriefDeliveryIntentRead,
  useDailyBrief,
} from "@/lib/ecom-api";
import {
  DailyBriefSection,
  FailurePanel,
  LoadingBlock,
  StatusCue,
  formatDateTime,
  querySurface,
  surfaceCopy,
} from "../../finance-ui";

function readParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : (value ?? null);
}

function DeliveryIntentTable({
  intents,
}: {
  intents: DailyBriefDeliveryIntentRead[];
}) {
  if (!intents.length) {
    return (
      <StatusCue
        state="pending"
        label="No delivery intents"
        detail="A03/Hermes native delivery has not created an intent for this brief."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)]">
      <div className="min-w-[760px]">
        <div className="grid grid-cols-[1fr_1fr_0.8fr_1.2fr_0.7fr_0.7fr] gap-3 border-b border-[color:var(--border)] px-4 py-3 text-xs font-semibold text-muted">
          <span>Target</span>
          <span>Status</span>
          <span className="text-right">Attempts</span>
          <span>Trace</span>
          <span>Delivered</span>
          <span>Packet</span>
        </div>
        {intents.map((intent) => (
          <div
            key={intent.id}
            className="grid grid-cols-[1fr_1fr_0.8fr_1.2fr_0.7fr_0.7fr] gap-3 border-b border-[color:var(--border)] px-4 py-3 text-sm last:border-b-0"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-strong">
                {intent.target_platform}
              </p>
              <p className="truncate text-xs text-muted">
                {intent.target_channel_ref}
              </p>
            </div>
            <div>
              <p className="font-medium text-strong">{intent.status}</p>
              <p className="truncate text-xs text-muted">
                {intent.error ?? intent.body_hash}
              </p>
            </div>
            <p className="text-right tabular-nums text-strong">
              {intent.attempt_count}
            </p>
            <p className="truncate text-muted">
              {intent.trace_id ?? "Trace pending"}
            </p>
            <p className="text-muted">
              {intent.delivered_at
                ? formatDateTime(intent.delivered_at)
                : "Not confirmed"}
            </p>
            <Link
              href={`/finance/daily-brief-delivery-intents/${intent.id}`}
              className="font-medium text-strong underline-offset-4 hover:underline"
            >
              Open
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DailyBriefDetailPage() {
  const params = useParams<{ briefId?: string | string[] }>();
  const briefId = readParam(params.briefId);
  const brief = useDailyBrief(briefId);
  const state = querySurface(brief);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Daily Brief Detail"
        subtitle={briefId ? `Brief ${briefId}` : "Missing brief id"}
        actions={
          <Link
            href="/finance"
            className="inline-flex min-h-9 items-center rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
          >
            Finance
          </Link>
        }
      />

      {!briefId ? (
        <FailurePanel
          icon={CircleSlash}
          title="Missing daily brief id"
          detail="A brief drilldown must name the exact stored brief. No latest/default brief is inferred."
        />
      ) : null}

      {briefId ? (
        <div className="grid gap-3 md:grid-cols-3">
          <StatusCue
            state={state}
            label="Brief read"
            detail={surfaceCopy(state, "daily brief")}
          />
          <StatusCue
            state={brief.data?.coverage.status ?? state}
            label="Coverage"
            detail={
              brief.data
                ? `${brief.data.coverage.percent}% · ${brief.data.coverage.freshness}`
                : "Awaiting brief data."
            }
          />
          <StatusCue
            state={brief.data?.narration_status ?? state}
            label="Narration"
            detail={
              brief.data?.narration_error ??
              "Deterministic fallback remains available."
            }
          />
        </div>
      ) : null}

      {state === "loading" ? <LoadingBlock label="Daily brief detail" /> : null}
      {briefId && state !== "loading" && brief.data ? (
        <div className="space-y-6">
          <DailyBriefSection brief={brief.data} />

          <section
            className="space-y-3"
            aria-labelledby="brief-metric-refs-heading"
          >
            <h2
              id="brief-metric-refs-heading"
              className="text-lg font-semibold text-strong"
            >
              Metric references
            </h2>
            {brief.data.metric_snapshot_ids.length ? (
              <div className="flex flex-wrap gap-2">
                {brief.data.metric_snapshot_ids.map((snapshotId) => (
                  <Link
                    key={snapshotId}
                    href={`/finance/metric-snapshots/${snapshotId}`}
                    className="inline-flex min-h-9 max-w-full items-center truncate rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
                  >
                    {snapshotId}
                  </Link>
                ))}
              </div>
            ) : (
              <StatusCue
                state="partial"
                label="No metric snapshots referenced"
                detail="The brief exists without attached finance metric snapshot references."
              />
            )}
          </section>

          <section
            className="space-y-3"
            aria-labelledby="delivery-intents-heading"
          >
            <h2
              id="delivery-intents-heading"
              className="text-lg font-semibold text-strong"
            >
              Delivery intents
            </h2>
            <DeliveryIntentTable intents={brief.data.delivery_intents} />
          </section>
        </div>
      ) : null}
      {briefId && state !== "loading" && !brief.data ? (
        <FailurePanel
          icon={
            state === "permission"
              ? LockKeyhole
              : state === "empty"
                ? CircleSlash
                : RefreshCcw
          }
          title={surfaceCopy(state, "daily brief")}
          detail="The detail route reads one persisted A08 brief by id and exposes fallback text, narration state, delivery status, evidence, and trace links when available."
        />
      ) : null}
    </div>
  );
}
