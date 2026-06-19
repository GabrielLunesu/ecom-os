"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { CircleSlash, LockKeyhole, RefreshCcw } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { useDailyBriefDeliveryPacket } from "@/lib/ecom-api";
import {
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

function EvidenceList({
  evidence,
}: {
  evidence: Array<Record<string, string>>;
}) {
  if (!evidence.length) {
    return <p className="text-sm text-muted">No evidence refs attached.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {evidence.map((item, index) => (
        <span
          key={`${item.type}-${item.id}-${index}`}
          className="inline-flex max-w-full items-center rounded-md border border-[color:var(--border)] px-2.5 py-1 text-xs text-muted"
        >
          <span className="truncate">
            {item.type}: {item.id}
          </span>
        </span>
      ))}
    </div>
  );
}

export default function DeliveryIntentPacketPage() {
  const params = useParams<{ intentId?: string | string[] }>();
  const intentId = readParam(params.intentId);
  const packet = useDailyBriefDeliveryPacket(intentId);
  const state = querySurface(packet);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Delivery Packet"
        subtitle={
          intentId ? `Intent ${intentId}` : "Missing delivery intent id"
        }
        actions={
          intentId && packet.data ? (
            <Link
              href={`/finance/daily-briefs/${packet.data.brief_id}`}
              className="inline-flex min-h-9 items-center rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
            >
              Brief
            </Link>
          ) : (
            <Link
              href="/finance"
              className="inline-flex min-h-9 items-center rounded-md border border-[color:var(--border-strong)] px-3 text-sm font-medium text-strong transition-colors hover:bg-[color:var(--surface-muted)]"
            >
              Finance
            </Link>
          )
        }
      />

      {!intentId ? (
        <FailurePanel
          icon={CircleSlash}
          title="Missing delivery intent id"
          detail="A dispatch packet must name the exact delivery intent. No latest/default delivery target is inferred."
        />
      ) : null}

      {intentId ? (
        <div className="grid gap-3 md:grid-cols-3">
          <StatusCue
            state={state}
            label="Packet read"
            detail={surfaceCopy(state, "delivery packet")}
          />
          <StatusCue
            state={
              packet.data?.dispatch_allowed
                ? "ready"
                : (packet.data?.dispatch_status ?? state)
            }
            label={
              packet.data?.dispatch_allowed
                ? "Dispatch allowed"
                : "Dispatch blocked"
            }
            detail={packet.data?.dispatch_status ?? "Awaiting packet data."}
          />
          <StatusCue
            state={packet.data?.body_hash_matches_intent ? "ready" : "error"}
            label="Body hash"
            detail={
              packet.data
                ? packet.data.body_hash_matches_intent
                  ? "Current body matches the stored delivery intent."
                  : "Current body differs from the stored delivery intent."
                : "Awaiting packet data."
            }
          />
        </div>
      ) : null}

      {state === "loading" ? <LoadingBlock label="Delivery packet" /> : null}
      {intentId && state !== "loading" && packet.data ? (
        <div className="space-y-6">
          <section
            className="grid gap-3 md:grid-cols-3"
            aria-label="Delivery target"
          >
            <StatusCue
              state={packet.data.intent.status}
              label={`Intent is ${packet.data.intent.status}`}
              detail={`${packet.data.target_platform} · ${packet.data.target_channel_ref}`}
            />
            <StatusCue
              state={packet.data.dispatch_status}
              label={`Dispatch status: ${packet.data.dispatch_status}`}
              detail={`Attempts: ${packet.data.intent.attempt_count}`}
            />
            <StatusCue
              state={packet.data.trace_id ? "ready" : "partial"}
              label="Trace"
              detail={packet.data.trace_id ?? "Trace pending"}
            />
          </section>

          {packet.data.warnings.length ? (
            <div className="rounded-lg border border-[color:rgba(180,83,9,0.35)] bg-[color:rgba(180,83,9,0.07)] p-4">
              <p className="text-sm font-semibold text-strong">Warnings</p>
              <ul className="mt-2 space-y-1 text-sm text-muted">
                {packet.data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <section className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
            <p className="text-sm font-semibold text-strong">Dispatch body</p>
            <pre className="mt-3 max-h-80 whitespace-pre-wrap break-words rounded-md bg-[color:var(--surface-muted)] p-3 font-sans text-sm leading-6 text-muted">
              {packet.data.body_text}
            </pre>
          </section>

          <section
            className="grid gap-3 md:grid-cols-2"
            aria-label="Dispatch hashes"
          >
            <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
              <p className="text-sm font-semibold text-strong">
                Idempotency key
              </p>
              <p className="mt-2 break-all font-mono text-xs text-muted">
                {packet.data.idempotency_key}
              </p>
            </div>
            <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4">
              <p className="text-sm font-semibold text-strong">Body hash</p>
              <p className="mt-2 break-all font-mono text-xs text-muted">
                {packet.data.body_hash}
              </p>
              <p className="mt-1 break-all font-mono text-xs text-muted">
                Intent: {packet.data.intent_body_hash}
              </p>
            </div>
          </section>

          <section
            className="space-y-3"
            aria-labelledby="packet-guardrails-heading"
          >
            <h2
              id="packet-guardrails-heading"
              className="text-lg font-semibold text-strong"
            >
              Guardrails
            </h2>
            <ul className="space-y-1 text-sm text-muted">
              {packet.data.guardrails.map((guardrail) => (
                <li key={guardrail}>{guardrail}</li>
              ))}
            </ul>
          </section>

          <section
            className="space-y-3"
            aria-labelledby="packet-evidence-heading"
          >
            <h2
              id="packet-evidence-heading"
              className="text-lg font-semibold text-strong"
            >
              Evidence
            </h2>
            <EvidenceList evidence={packet.data.evidence} />
          </section>

          <p className="text-sm text-muted">
            Updated {formatDateTime(packet.data.intent.updated_at)}
          </p>
        </div>
      ) : null}

      {intentId && state !== "loading" && !packet.data ? (
        <FailurePanel
          icon={
            state === "permission"
              ? LockKeyhole
              : state === "empty"
                ? CircleSlash
                : RefreshCcw
          }
          title={surfaceCopy(state, "delivery packet")}
          detail="The packet route reads one persisted A08 delivery intent and never sends a native channel message."
        />
      ) : null}
    </div>
  );
}
