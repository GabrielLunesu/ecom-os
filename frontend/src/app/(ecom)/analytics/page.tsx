"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/ecom/PageHeader";
import { KpiCard } from "@/components/ecom/KpiCard";
import { cn } from "@/lib/utils";
import { listContainer } from "@/lib/design/tokens";
import { ALL_STORES, useStore } from "@/components/ecom/store-context";
import { useMetrics } from "@/lib/ecom-api";

const RANGES = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
] as const;

export default function AnalyticsPage() {
  const { activeStoreId, isAggregate } = useStore();
  const scope = activeStoreId === ALL_STORES ? "all" : activeStoreId;
  const [days, setDays] = useState<number>(30);
  const { data, isLoading } = useMetrics(scope, days);
  const k = data?.kpis;

  const bars = (data?.per_store ?? []).map((s) => ({
    name: s.store_name,
    revenue: s.revenue,
    orders: s.orders,
  }));

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle={`${isAggregate ? "All stores" : "Store"} · order-derived metrics`}
        actions={
          <div className="flex gap-1 rounded-lg bg-[color:var(--surface-muted)] p-1 text-sm">
            {RANGES.map((r) => (
              <button
                key={r.days}
                type="button"
                onClick={() => setDays(r.days)}
                className={cn(
                  "rounded-md px-2.5 py-1 font-medium transition-colors",
                  days === r.days
                    ? "bg-[color:var(--surface)] text-strong shadow-sm"
                    : "text-muted hover:text-strong",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        }
      />

      <motion.div
        variants={listContainer}
        initial="hidden"
        animate="show"
        className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4"
      >
        <KpiCard label="Revenue" value={k?.revenue ?? 0} prefix="$" decimals={2} loading={isLoading} />
        <KpiCard label="Orders" value={k?.orders ?? 0} loading={isLoading} />
        <KpiCard label="AOV" value={k?.aov ?? 0} prefix="$" decimals={2} loading={isLoading} />
        <KpiCard
          label="Conversion"
          value={0}
          suffix="%"
          loading={isLoading}
          unavailable={data?.unavailable?.conversion}
        />
      </motion.div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
          <p className="mb-3 text-sm font-semibold text-strong">Revenue by store</p>
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bars} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-muted)" }} />
                <YAxis tick={{ fontSize: 12, fill: "var(--text-muted)" }} />
                <Tooltip
                  cursor={{ fill: "var(--surface-muted)" }}
                  contentStyle={{
                    borderRadius: 10,
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-card)",
                    fontSize: 13,
                  }}
                />
                <Bar dataKey="revenue" radius={[6, 6, 0, 0]}>
                  {bars.map((_, i) => (
                    <Cell key={i} fill="var(--accent)" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
          <p className="mb-3 text-sm font-semibold text-strong">Conversion funnel</p>
          <div className="space-y-2 text-sm">
            {[
              { stage: "Sessions", v: data?.unavailable?.sessions },
              { stage: "Add to cart", v: data?.unavailable?.atc_rate },
              { stage: "Checkout", v: data?.unavailable?.conversion },
              { stage: "Orders", v: null as string | null | undefined },
            ].map((row, i) => (
              <div
                key={row.stage}
                className="flex items-center justify-between rounded-lg bg-[color:var(--surface-muted)] px-3 py-2"
                style={{ width: `${100 - i * 12}%` }}
              >
                <span className="text-strong">{row.stage}</span>
                <span className="tabular-nums text-quiet">
                  {row.stage === "Orders" ? (k?.orders ?? 0) : "n/a"}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-quiet">
            Session/funnel metrics need Shopify Analytics (<code>read_reports</code>).
          </p>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card">
        <div className="grid grid-cols-4 gap-2 border-b border-[color:var(--border)] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-quiet">
          <span>Store</span>
          <span className="text-right">Revenue</span>
          <span className="text-right">Orders</span>
          <span className="text-right">AOV</span>
        </div>
        {(data?.per_store ?? []).map((s) => (
          <div key={s.store_id} className="grid grid-cols-4 gap-2 px-4 py-2.5 text-sm">
            <span className="truncate text-strong">{s.store_name}</span>
            <span className="text-right tabular-nums text-strong">${s.revenue.toFixed(2)}</span>
            <span className="text-right tabular-nums text-muted">{s.orders}</span>
            <span className="text-right tabular-nums text-muted">${s.aov.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
