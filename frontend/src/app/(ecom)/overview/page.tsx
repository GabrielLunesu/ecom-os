"use client";

import { motion } from "framer-motion";

import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { KpiCard } from "@/components/ecom/KpiCard";
import { cn } from "@/lib/utils";
import { listContainer, listItem } from "@/lib/design/tokens";
import { ALL_STORES, useStore } from "@/components/ecom/store-context";
import { useInsights, useMetrics } from "@/lib/ecom-api";

export default function OverviewPage() {
  const { isAggregate, activeStore, activeStoreId } = useStore();
  const scopeLabel = isAggregate ? "All stores" : (activeStore?.name ?? "store");
  const scope = activeStoreId === ALL_STORES ? "all" : activeStoreId;

  const { data, isLoading } = useMetrics(scope, 30);
  const insights = useInsights();
  const k = data?.kpis;
  const unavailable = data?.unavailable ?? {};

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle={`${scopeLabel} · last 30 days`}
      />

      <motion.div
        variants={listContainer}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-3 md:grid-cols-3"
      >
        <KpiCard
          label="Revenue"
          value={k?.revenue ?? 0}
          prefix="$"
          decimals={2}
          loading={isLoading}
        />
        <KpiCard label="Orders" value={k?.orders ?? 0} loading={isLoading} />
        <KpiCard
          label="AOV"
          value={k?.aov ?? 0}
          prefix="$"
          decimals={2}
          loading={isLoading}
        />
        <KpiCard
          label="Sessions"
          value={0}
          loading={isLoading}
          unavailable={unavailable.sessions}
        />
        <KpiCard
          label="Conversion"
          value={0}
          suffix="%"
          decimals={2}
          loading={isLoading}
          unavailable={unavailable.conversion}
        />
        <KpiCard
          label="ATC rate"
          value={0}
          suffix="%"
          decimals={2}
          loading={isLoading}
          unavailable={unavailable.atc_rate}
        />
      </motion.div>

      <div className="mt-6">
        <h2 className="mb-2 text-sm font-semibold tracking-[-0.01em] text-strong">Insights</h2>
        <motion.div
          variants={listContainer}
          initial="hidden"
          animate="show"
          className="grid gap-2 md:grid-cols-3"
        >
          {(insights.data ?? []).map((ins, i) => {
            const Icon =
              ins.severity === "warning"
                ? AlertTriangle
                : ins.severity === "info" && ins.title.toLowerCase().includes("track")
                  ? CheckCircle2
                  : Info;
            return (
              <motion.div
                key={i}
                variants={listItem}
                className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-3.5 shadow-card"
              >
                <div className="flex items-start gap-2.5">
                  <Icon
                    className={cn(
                      "mt-0.5 h-4 w-4 shrink-0",
                      ins.severity === "warning"
                        ? "text-[color:var(--warning)]"
                        : "text-[color:var(--success)]",
                    )}
                  />
                  <div>
                    <p className="text-sm font-medium text-strong">{ins.title}</p>
                    <p className="mt-0.5 text-xs text-quiet">{ins.detail}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>

      <p className="mt-6 text-sm text-quiet">
        Revenue, orders, and AOV are live from Shopify. Session-based metrics need
        Shopify Analytics access (<code>read_reports</code>) and are shown as n/a.
      </p>
    </div>
  );
}
