"use client";

import { motion } from "framer-motion";

import { PageHeader } from "@/components/ecom/PageHeader";
import { KpiCard } from "@/components/ecom/KpiCard";
import { listContainer } from "@/lib/design/tokens";
import { useStore } from "@/components/ecom/store-context";

const KPIS = [
  { label: "Revenue", prefix: "$" },
  { label: "Orders" },
  { label: "AOV", prefix: "$", decimals: 2 },
  { label: "Sessions" },
  { label: "Conversion", suffix: "%", decimals: 2 },
  { label: "ATC rate", suffix: "%", decimals: 2 },
] as const;

export default function OverviewPage() {
  const { isAggregate, activeStore } = useStore();
  const scope = isAggregate ? "All stores" : (activeStore?.name ?? "store");

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle={`${scope} · brand and per-store KPIs`}
      />

      {/* KPIs render in skeleton state until the Shopify read slice wires live
          data (Build order §3). The card + animated counter design is in place. */}
      <motion.div
        variants={listContainer}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-3 md:grid-cols-3"
      >
        {KPIS.map((k) => (
          <KpiCard key={k.label} value={0} loading {...k} />
        ))}
      </motion.div>

      <p className="mt-6 text-sm text-quiet">
        Live KPIs activate when the Shopify read slice ships. Store scope and the
        aggregate view are wired end-to-end.
      </p>
    </div>
  );
}
