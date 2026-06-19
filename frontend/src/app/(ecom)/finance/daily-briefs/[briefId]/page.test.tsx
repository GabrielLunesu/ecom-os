import type React from "react";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DailyBriefDetailPage from "./page";

const useParamsMock = vi.fn();
const useDailyBriefMock = vi.fn();

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
    useDailyBrief: () => useDailyBriefMock(),
  };
});

const brief = {
  id: "brief_1",
  store_id: "store_1",
  schema_version: 1,
  revision: 2,
  status: "finalized",
  window: {
    reporting_date: "2026-06-18",
    timezone: "America/New_York",
    start_utc: "2026-06-18T04:00:00Z",
    end_utc: "2026-06-19T04:00:00Z",
  },
  coverage: {
    status: "partial",
    percent: 80,
    freshness: "stale",
    missing_component_kinds: [],
    warnings: ["Ad spend is stale."],
  },
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
  deterministic_fallback_text: "Fallback brief body.",
  final_text: "Narrated body with unchanged numbers.",
  final_body_hash: "abcdef1234567890",
  narration_status: "narrated",
  narration_error: null,
  hermes_session_id: "session_1",
  hermes_run_id: "run_1",
  hermes_cron_ref: "cron_1",
  trace_id: "trace_brief",
  created_at: "2026-06-19T07:00:00Z",
  finalized_at: "2026-06-19T07:00:00Z",
  delivered_at: null,
  delivery_intents: [
    {
      id: "intent_1",
      brief_id: "brief_1",
      target_platform: "hermes_channel",
      target_channel_ref: "slack:ops",
      idempotency_key: "brief_1/hermes_channel/slack:ops",
      status: "outcome_unknown",
      body_hash: "abcdef1234567890",
      delivery_evidence: { provider_id: "msg_1" },
      attempt_count: 2,
      trace_id: "trace_delivery",
      error: "transport interrupted after dispatch",
      created_at: "2026-06-19T07:00:00Z",
      updated_at: "2026-06-19T07:05:00Z",
      delivered_at: null,
    },
  ],
};

describe("/finance/daily-briefs/[briefId]", () => {
  beforeEach(() => {
    useParamsMock.mockReset();
    useDailyBriefMock.mockReset();
    useParamsMock.mockReturnValue({ briefId: "brief_1" });
    useDailyBriefMock.mockReturnValue({
      data: brief,
      isLoading: false,
      error: null,
    });
  });

  it("renders one exact daily brief with delivery status and metric refs", () => {
    render(<DailyBriefDetailPage />);

    expect(
      screen.getByRole("heading", { name: "Daily Brief Detail" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Narrated body with unchanged numbers."),
    ).toBeInTheDocument();
    expect(screen.getByText("outcome_unknown")).toBeInTheDocument();
    expect(
      screen.getByText("transport interrupted after dispatch"),
    ).toBeInTheDocument();
    expect(screen.getByText("Open")).toHaveAttribute(
      "href",
      "/finance/daily-brief-delivery-intents/intent_1",
    );
    expect(screen.getByText("snapshot_1")).toHaveAttribute(
      "href",
      "/finance/metric-snapshots/snapshot_1",
    );
    expect(screen.getByText("Finance")).toHaveAttribute("href", "/finance");
  });

  it("does not infer a latest brief when the id is absent", () => {
    useParamsMock.mockReturnValue({});

    render(<DailyBriefDetailPage />);

    expect(screen.getByText("Missing daily brief id")).toBeInTheDocument();
    expect(
      screen.queryByText("Narrated body with unchanged numbers."),
    ).not.toBeInTheDocument();
  });
});
