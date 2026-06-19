import type React from "react";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MetricSnapshotDetailPage from "./page";

const useParamsMock = vi.fn();
const useMetricSnapshotMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
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
    useMetricSnapshot: () => useMetricSnapshotMock(),
  };
});

const snapshot = {
  id: "snapshot_1",
  metric_name: "estimated_contribution_margin",
  display_name: "Estimated contribution margin",
  formula_version: "estimated_contribution_margin.v1",
  schema_version: 1,
  store_id: "store_1",
  value: { minor: 32100, currency: "USD" },
  window: {
    reporting_date: "2026-06-18",
    timezone: "America/New_York",
    start_utc: "2026-06-18T04:00:00Z",
    end_utc: "2026-06-19T04:00:00Z",
  },
  coverage: {
    status: "partial",
    percent: 75,
    freshness: "current",
    missing_component_kinds: ["cogs"],
    warnings: ["COGS is missing."],
  },
  attribution_window_days: 7,
  fx_basis: "source_currency_only",
  trace_id: "trace_metric",
  calculation_status: "finalized",
  created_at: "2026-06-19T07:00:00Z",
  finalized_at: "2026-06-19T07:00:00Z",
  components: [
    {
      id: "component_1",
      kind: "net_sales",
      amount: { minor: 50000, currency: "USD" },
      contribution: { minor: 50000, currency: "USD" },
      source_ref: "shopify_order:2001",
      source_timestamp: "2026-06-18T12:00:00Z",
      collected_at: "2026-06-19T07:00:00Z",
      coverage: "verified",
      freshness: "current",
      evidence_refs: ["order:2001"],
    },
  ],
};

describe("/finance/metric-snapshots/[snapshotId]", () => {
  beforeEach(() => {
    useParamsMock.mockReset();
    useMetricSnapshotMock.mockReset();
    useParamsMock.mockReturnValue({ snapshotId: "snapshot_1" });
    useMetricSnapshotMock.mockReturnValue({
      data: snapshot,
      isLoading: false,
      error: null,
    });
  });

  it("renders one exact metric snapshot and narration guardrails", () => {
    render(<MetricSnapshotDetailPage />);

    expect(
      screen.getByRole("heading", { name: "Metric Detail" }),
    ).toBeInTheDocument();
    expect(screen.getByText("$321.00")).toBeInTheDocument();
    expect(screen.getByText(/Missing: Cogs/)).toBeInTheDocument();
    expect(screen.getByText("shopify_order:2001")).toBeInTheDocument();
    expect(
      screen.getByText("Do not recalculate or alter metric values."),
    ).toBeInTheDocument();
    expect(screen.getByText("Finance")).toHaveAttribute("href", "/finance");
  });

  it("does not infer a latest snapshot when the id is absent", () => {
    useParamsMock.mockReturnValue({});

    render(<MetricSnapshotDetailPage />);

    expect(screen.getByText("Missing metric snapshot id")).toBeInTheDocument();
    expect(screen.queryByText("$321.00")).not.toBeInTheDocument();
  });
});
