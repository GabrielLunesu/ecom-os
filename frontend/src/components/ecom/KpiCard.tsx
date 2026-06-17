"use client";

import { motion } from "framer-motion";

import { cn } from "@/lib/utils";
import { listItem, spring } from "@/lib/design/tokens";
import { AnimatedNumber } from "@/lib/design/AnimatedNumber";

type Props = {
  label: string;
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  delta?: number; // percent change vs comparison period
  loading?: boolean;
};

/** A single KPI tile with an animated counter and soft elevation. */
export function KpiCard({
  label,
  value,
  decimals = 0,
  prefix,
  suffix,
  delta,
  loading,
}: Props) {
  return (
    <motion.div
      variants={listItem}
      whileHover={{ y: -2 }}
      transition={spring.snappy}
      className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
    >
      <p className="text-[13px] font-medium text-muted">{label}</p>
      {loading ? (
        <div className="mt-2 h-8 w-24 animate-pulse rounded-md bg-[color:var(--surface-muted)]" />
      ) : (
        <div className="mt-1.5 flex items-baseline gap-2">
          <span className="text-[28px] font-semibold tracking-[-0.02em] text-strong">
            <AnimatedNumber
              value={value}
              decimals={decimals}
              prefix={prefix}
              suffix={suffix}
            />
          </span>
          {typeof delta === "number" ? (
            <span
              className={cn(
                "text-xs font-medium tabular-nums",
                delta >= 0 ? "text-[color:var(--success)]" : "text-[color:var(--danger)]",
              )}
            >
              {delta >= 0 ? "+" : ""}
              {delta.toFixed(1)}%
            </span>
          ) : null}
        </div>
      )}
    </motion.div>
  );
}
