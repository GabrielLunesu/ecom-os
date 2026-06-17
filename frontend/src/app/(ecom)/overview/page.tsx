"use client";

import { motion } from "framer-motion";

import { PageHeader } from "@/components/ecom/PageHeader";
import { KpiCard } from "@/components/ecom/KpiCard";
import { listContainer } from "@/lib/design/tokens";
import { ALL_STORES, useStore } from "@/components/ecom/store-context";
import { useMetrics } from "@/lib/ecom-api";

export default function OverviewPage() {
  const { isAggregate, activeStore, activeStoreId } = useStore();
  const scopeLabel = isAggregate ? "All stores" : (activeStore?.name ?? "store");
  const scope = activeStoreId === ALL_STORES ? "all" : activeStoreId;

  const { data, isLoading } = useMetrics(scope, 30);
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

      <p className="mt-6 text-sm text-quiet">
        Revenue, orders, and AOV are live from Shopify. Session-based metrics need
        Shopify Analytics access (<code>read_reports</code>) and are shown as n/a.
      </p>
    </div>
  );
}
