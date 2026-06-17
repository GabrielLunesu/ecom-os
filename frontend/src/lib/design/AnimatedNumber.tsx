"use client";

import { useEffect } from "react";
import {
  animate,
  useMotionValue,
  useReducedMotion,
  useTransform,
  motion,
} from "framer-motion";

import { duration, easing } from "./tokens";

type Props = {
  value: number;
  /** Decimal places to render. */
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
};

/** Spring-eased KPI counter with tabular figures (Build Spec §3). Respects
 * prefers-reduced-motion by snapping straight to the value. */
export function AnimatedNumber({
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
  className,
}: Props) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) =>
    `${prefix}${v.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}${suffix}`,
  );

  useEffect(() => {
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, {
      duration: duration.slow,
      ease: easing.standard,
    });
    return () => controls.stop();
  }, [mv, value, reduce]);

  return (
    <motion.span className={className} style={{ fontVariantNumeric: "tabular-nums" }}>
      {text}
    </motion.span>
  );
}
