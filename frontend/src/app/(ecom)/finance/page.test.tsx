import type React from "react";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FinancePage from "./page";

const useStoreMock = vi.fn();
const useLatestMetricSnapshotMock = vi.fn();
const useLatestDailyBriefMock = vi.fn();

vi.mock("@/components/ecom/store-context", () => ({
  ALL_STORES: "all",
  useStore: () => useStoreMock(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: React.PropsWithChildren<{ href: string }>) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/ecom-api", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/ecom-api")>("@/lib/ecom-api");
  return {
    ...actual,
    useLatestMetricSnapshot: () => useLatestMetricSnapshotMock(),
    useLatestDailyBrief: () => useLatestDailyBriefMock(),
  };
});

const metricSnapshot = {
  id: "snapshot_1",
  metric_name: "estimated_contribution_margin",
  display_name: "Estimated contribution margin",
  formula_version: "estimated_contribution_margin.v1",
  schema_version: 1,
  store_id: "store_1",
  value: { minor: 12345, currency: "USD" },
  window: {
    reporting_date: "2026-06-18",
    timezone: "America/New_York",
    start_utc: "2026-06-18T04:00:00Z",
    end_utc: "2026-06-19T04:00:00Z",
  },
  coverage: {
    status: "partial",
    percent: 66,
    freshness: "stale",
    missing_component_kinds: ["ad_spend", "payment_fees"],
    warnings: ["Ad spend is unavailable for this window."],
  },
  attribution_window_days: 7,
  fx_basis: "source_currency_only",
  trace_id: "trace_1",
  calculation_status: "finalized",
  created_at: "2026-06-19T07:00:00Z",
  finalized_at: "2026-06-19T07:00:00Z",
  components: [
    {
      id: "component_1",
      kind: "net_sales",
      amount: { minor: 20000, currency: "USD" },
      contribution: { minor: 20000, currency: "USD" },
      source_ref: "shopify_order:1001",
      source_timestamp: "2026-06-18T12:00:00Z",
      collected_at: "2026-06-19T07:00:00Z",
      coverage: "verified",
      freshness: "current",
      evidence_refs: ["order:1001"],
    },
  ],
};

const dailyBrief = {
  id: "brief_1",
  store_id: "store_1",
  schema_version: 1,
  revision: 1,
  status: "finalized",
  window: metricSnapshot.window,
  coverage: metricSnapshot.coverage,
  metric_snapshot_ids: ["snapshot_1"],
  sections: [
    {
      kind: "economics",
      title: "Economics",
      coverage: "partial",
      freshness: "stale",
      items: [],
      warnings: [],
      evidence_refs: ["snapshot_1"],
    },
  ],
  deterministic_fallback_text: "Daily brief fallback text.",
  final_text: null,
  final_body_hash: "abcdef1234567890",
  narration_status: "fallback",
  narration_error: null,
  hermes_session_id: null,
  hermes_run_id: null,
  hermes_cron_ref: null,
  trace_id: "trace_1",
  created_at: "2026-06-19T07:00:00Z",
  finalized_at: "2026-06-19T07:00:00Z",
  delivered_at: null,
  delivery_intents: [],
};

describe("/finance", () => {
  beforeEach(() => {
    useStoreMock.mockReset();
    useLatestMetricSnapshotMock.mockReset();
    useLatestDailyBriefMock.mockReset();
    useLatestMetricSnapshotMock.mockReturnValue({
      data: metricSnapshot,
      isLoading: false,
      error: null,
    });
    useLatestDailyBriefMock.mockReturnValue({
      data: dailyBrief,
      isLoading: false,
      error: null,
    });
  });

  it("renders deterministic finance evidence for an exact store", () => {
    useStoreMock.mockReturnValue({
      activeStore: { id: "store_1", name: "North Store", domain: "north.test" },
      activeStoreId: "store_1",
      isAggregate: false,
    });

    render(<FinancePage />);

    expect(
      screen.getByRole("heading", { name: "Finance" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/North Store/)).toBeInTheDocument();
    expect(screen.getByText("$123.45")).toBeInTheDocument();
    expect(
      screen.getByText(
        "estimated_contribution_margin.v1 · America/New_York · 7-day attribution",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Missing: Ad Spend, Payment Fees/),
    ).toBeInTheDocument();
    expect(screen.getByText("shopify_order:1001")).toBeInTheDocument();
    expect(screen.getByText("Daily brief fallback text.")).toBeInTheDocument();
  });

  it("requires a selected store instead of using an aggregate or default", () => {
    useStoreMock.mockReturnValue({
      activeStore: null,
      activeStoreId: "all",
      isAggregate: true,
    });

    render(<FinancePage />);

    expect(screen.getByText("Select one exact store")).toBeInTheDocument();
    expect(screen.getByText(/do not choose a default/)).toBeInTheDocument();
    expect(screen.queryByText("$123.45")).not.toBeInTheDocument();
  });
});
