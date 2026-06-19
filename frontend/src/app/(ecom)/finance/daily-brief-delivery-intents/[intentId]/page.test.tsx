import type React from "react";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DeliveryIntentPacketPage from "./page";

const useParamsMock = vi.fn();
const useDailyBriefDeliveryPacketMock = vi.fn();

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
    useDailyBriefDeliveryPacket: () => useDailyBriefDeliveryPacketMock(),
  };
});

const packet = {
  intent: {
    id: "intent_1",
    brief_id: "brief_1",
    target_platform: "hermes_native",
    target_channel_ref: "slack:ops",
    idempotency_key: "daily_brief:brief_1:hermes_native:slack:ops",
    status: "outcome_unknown",
    body_hash: "hash_1",
    delivery_evidence: { provider: "hermes" },
    attempt_count: 2,
    trace_id: "trace_delivery",
    error: "timeout after dispatch",
    created_at: "2026-06-19T07:00:00Z",
    updated_at: "2026-06-19T07:05:00Z",
    delivered_at: null,
  },
  brief_id: "brief_1",
  store_id: "store_1",
  reporting_date: "2026-06-18",
  reporting_timezone: "America/New_York",
  target_platform: "hermes_native",
  target_channel_ref: "slack:ops",
  idempotency_key: "daily_brief:brief_1:hermes_native:slack:ops",
  body_text: "Daily brief body.",
  body_hash: "hash_1",
  intent_body_hash: "hash_1",
  body_hash_matches_intent: true,
  dispatch_allowed: false,
  dispatch_status: "reconcile_before_retry",
  trace_id: "trace_delivery",
  evidence: [
    { type: "daily_brief", id: "brief_1" },
    { type: "metric_snapshot", id: "snapshot_1" },
  ],
  warnings: [
    "Delivery outcome is unknown; reconcile the provider result before retrying.",
  ],
  guardrails: [
    "A08 does not send native channel messages.",
    "Use Hermes-native channel delivery only.",
    "Use the provided idempotency key for dispatch attempts.",
  ],
};

describe("/finance/daily-brief-delivery-intents/[intentId]", () => {
  beforeEach(() => {
    useParamsMock.mockReset();
    useDailyBriefDeliveryPacketMock.mockReset();
    useParamsMock.mockReturnValue({ intentId: "intent_1" });
    useDailyBriefDeliveryPacketMock.mockReturnValue({
      data: packet,
      isLoading: false,
      error: null,
    });
  });

  it("renders dispatch packet guardrails and blocked retry state", () => {
    render(<DeliveryIntentPacketPage />);

    expect(
      screen.getByRole("heading", { name: "Delivery Packet" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Dispatch blocked")).toBeInTheDocument();
    expect(
      screen.getAllByText("reconcile_before_retry").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Daily brief body.")).toBeInTheDocument();
    expect(
      screen.getByText("daily_brief:brief_1:hermes_native:slack:ops"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("A08 does not send native channel messages."),
    ).toBeInTheDocument();
    expect(screen.getByText("daily_brief: brief_1")).toBeInTheDocument();
    expect(screen.getByText("Brief")).toHaveAttribute(
      "href",
      "/finance/daily-briefs/brief_1",
    );
  });

  it("does not infer a delivery packet when the intent id is absent", () => {
    useParamsMock.mockReturnValue({});

    render(<DeliveryIntentPacketPage />);

    expect(
      screen.getAllByText("Missing delivery intent id").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Finance")).toHaveAttribute("href", "/finance");
    expect(screen.queryByText("Daily brief body.")).not.toBeInTheDocument();
  });
});
