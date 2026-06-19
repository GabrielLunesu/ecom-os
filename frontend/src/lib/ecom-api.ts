"use client";

import { useQuery } from "@tanstack/react-query";

import { customFetch } from "@/api/mutator";

/** Typed client for the Ecom-OS backend endpoints (reuses the shared auth +
 * base-URL mutator). Connection refs / status only — never secrets. */

export type EcomStore = {
  id: string;
  name: string;
  domain: string;
  provider: string;
  status: string;
  public_url?: string;
  support_email?: string;
  support_name?: string;
  tracking_url?: string;
  facts?: string;
};

export type StoreProfile = {
  name: string;
  public_url: string;
  support_email: string;
  support_name: string;
  tracking_url: string;
  facts: string;
};

export const setStoreProfile = async (
  id: string,
  profile: StoreProfile,
): Promise<EcomStore> =>
  (
    await customFetch<Wrapped<EcomStore>>(`/api/v1/ecom/stores/${id}/profile`, {
      method: "PUT",
      body: JSON.stringify(profile),
    })
  ).data;

/** Connect a store with its app's client id + secret. The app mints + refreshes
 * the Admin API token via the client-credentials grant (no browser, no raw token). */
export const connectShopify = async (
  id: string,
  client_id: string,
  client_secret: string,
): Promise<EcomStore> =>
  (
    await customFetch<Wrapped<EcomStore>>(
      `/api/v1/ecom/stores/${id}/shopify-credentials`,
      { method: "PUT", body: JSON.stringify({ client_id, client_secret }) },
    )
  ).data;

export type ProviderHealth = {
  provider: string;
  connected: boolean;
  detail: string;
};

export type Connections = {
  ready: boolean;
  providers: ProviderHealth[];
};

/** customFetch wraps responses as { data, status, headers } — unwrap to the body. */
type Wrapped<T> = { data: T; status: number };

export const fetchStores = async (): Promise<EcomStore[]> =>
  (
    await customFetch<Wrapped<EcomStore[]>>("/api/v1/ecom/stores", {
      method: "GET",
    })
  ).data;

export const fetchConnections = async (): Promise<Connections> =>
  (
    await customFetch<Wrapped<Connections>>("/api/v1/ecom/connections", {
      method: "GET",
    })
  ).data;

export type Kpis = {
  revenue: number;
  orders: number;
  aov: number;
  currency: string;
  sessions: number | null;
  conversion: number | null;
  atc_rate: number | null;
};

export type Metrics = {
  scope: string;
  days: number;
  kpis: Kpis;
  per_store: Array<Kpis & { store_id: string; store_name: string }>;
  unavailable: Record<string, string>;
};

export const fetchMetrics = async (
  store: string,
  days: number,
): Promise<Metrics> =>
  (
    await customFetch<Wrapped<Metrics>>(
      `/api/v1/ecom/metrics?store=${encodeURIComponent(store)}&days=${days}`,
      { method: "GET" },
    )
  ).data;

export function useMetrics(store: string, days: number) {
  return useQuery({
    queryKey: ["ecom", "metrics", store, days],
    queryFn: () => fetchMetrics(store, days),
    staleTime: 30_000,
  });
}

// --- Finance metrics and daily brief (A08 exported router, mounted by integration owner) ---
export type MoneyRead = {
  minor: number;
  currency: string;
};

export type ReportingWindowRead = {
  reporting_date: string;
  timezone: string;
  start_utc: string;
  end_utc: string;
};

export type CoverageRead = {
  status: string;
  percent: number;
  freshness: string;
  missing_component_kinds: string[];
  warnings: string[];
};

export type MetricComponentRead = {
  id: string;
  kind: string;
  amount: MoneyRead;
  contribution: MoneyRead;
  source_ref: string;
  source_timestamp: string;
  collected_at: string;
  coverage: string;
  freshness: string;
  evidence_refs: string[];
};

export type MetricSnapshotDetail = {
  id: string;
  metric_name: string;
  display_name: string;
  formula_version: string;
  schema_version: number;
  store_id: string;
  value: MoneyRead;
  window: ReportingWindowRead;
  coverage: CoverageRead;
  attribution_window_days: number;
  fx_basis: string;
  trace_id: string | null;
  calculation_status: string;
  created_at: string;
  finalized_at: string;
  components: MetricComponentRead[];
};

export type MetricCardSummary = {
  snapshot_id: string;
  store_id: string;
  title: string;
  metric_name: string;
  value: MoneyRead;
  formula_version: string;
  reporting_date: string;
  reporting_timezone: string;
  window_start_utc: string;
  window_end_utc: string;
  coverage_status: string;
  coverage_percent: number;
  freshness: string;
  calculation_status: string;
  trace_id: string | null;
  warnings: string[];
  missing_component_kinds: string[];
  component_count: number;
  detail_ref: string;
};

export type DailyBriefSectionRead = {
  kind: string;
  title: string;
  coverage: string;
  freshness: string;
  items: Array<Record<string, unknown>>;
  warnings: string[];
  evidence_refs: string[];
};

export type DailyBriefDeliveryIntentRead = {
  id: string;
  brief_id: string;
  target_platform: string;
  target_channel_ref: string;
  idempotency_key: string;
  status: string;
  body_hash: string;
  delivery_evidence: Record<string, unknown>;
  attempt_count: number;
  trace_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  delivered_at: string | null;
};

export type DailyBriefDeliveryPacket = {
  intent: DailyBriefDeliveryIntentRead;
  brief_id: string;
  store_id: string;
  reporting_date: string;
  reporting_timezone: string;
  target_platform: string;
  target_channel_ref: string;
  idempotency_key: string;
  body_text: string;
  body_hash: string;
  intent_body_hash: string;
  body_hash_matches_intent: boolean;
  dispatch_allowed: boolean;
  dispatch_status: string;
  trace_id: string | null;
  evidence: Array<Record<string, string>>;
  warnings: string[];
  guardrails: string[];
};

export type DailyBriefDetail = {
  id: string;
  store_id: string;
  schema_version: number;
  revision: number;
  status: string;
  window: ReportingWindowRead;
  coverage: CoverageRead;
  metric_snapshot_ids: string[];
  sections: DailyBriefSectionRead[];
  deterministic_fallback_text: string;
  final_text: string | null;
  final_body_hash: string;
  narration_status: string;
  narration_error: string | null;
  hermes_session_id: string | null;
  hermes_run_id: string | null;
  hermes_cron_ref: string | null;
  trace_id: string | null;
  created_at: string;
  finalized_at: string;
  delivered_at: string | null;
  delivery_intents: DailyBriefDeliveryIntentRead[];
};

export type BriefCardSummary = {
  brief_id: string;
  store_id: string;
  title: string;
  status: string;
  reporting_date: string;
  reporting_timezone: string;
  window_start_utc: string;
  window_end_utc: string;
  coverage_status: string;
  coverage_percent: number;
  freshness: string;
  narration_status: string;
  delivery_status: string;
  delivery_target_count: number;
  pending_delivery_count: number;
  failed_delivery_count: number;
  outcome_unknown_delivery_count: number;
  delivered_at: string | null;
  trace_id: string | null;
  warnings: string[];
  metric_snapshot_ids: string[];
  detail_ref: string;
};

const financeParams = (
  storeId: string,
  params?: Record<string, string | undefined>,
) => {
  const search = new URLSearchParams({ store_id: storeId });
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) search.set(key, value);
  }
  return search.toString();
};

export const fetchLatestMetricSnapshot = async (
  storeId: string,
  currency?: string,
): Promise<MetricSnapshotDetail> =>
  (
    await customFetch<Wrapped<MetricSnapshotDetail>>(
      `/api/v1/ecom/finance/metric-snapshots/latest?${financeParams(storeId, {
        currency,
      })}`,
      { method: "GET" },
    )
  ).data;

export const fetchMetricSnapshot = async (
  snapshotId: string,
): Promise<MetricSnapshotDetail> =>
  (
    await customFetch<Wrapped<MetricSnapshotDetail>>(
      `/api/v1/ecom/finance/metric-snapshots/${encodeURIComponent(snapshotId)}`,
      { method: "GET" },
    )
  ).data;

export const fetchLatestMetricCard = async (
  storeId: string,
  currency?: string,
  metricName = "estimated_contribution_margin",
): Promise<MetricCardSummary> =>
  (
    await customFetch<Wrapped<MetricCardSummary>>(
      `/api/v1/ecom/finance/metric-snapshots/latest/card?${financeParams(
        storeId,
        {
          currency,
          metric_name: metricName,
        },
      )}`,
      { method: "GET" },
    )
  ).data;

export const fetchMetricCard = async (
  snapshotId: string,
): Promise<MetricCardSummary> =>
  (
    await customFetch<Wrapped<MetricCardSummary>>(
      `/api/v1/ecom/finance/metric-snapshots/${encodeURIComponent(snapshotId)}/card`,
      { method: "GET" },
    )
  ).data;

export const fetchLatestDailyBrief = async (
  storeId: string,
): Promise<DailyBriefDetail> =>
  (
    await customFetch<Wrapped<DailyBriefDetail>>(
      `/api/v1/ecom/finance/daily-briefs/latest?${financeParams(storeId)}`,
      { method: "GET" },
    )
  ).data;

export const fetchDailyBrief = async (
  briefId: string,
): Promise<DailyBriefDetail> =>
  (
    await customFetch<Wrapped<DailyBriefDetail>>(
      `/api/v1/ecom/finance/daily-briefs/${encodeURIComponent(briefId)}`,
      { method: "GET" },
    )
  ).data;

export const fetchDailyBriefDeliveryPacket = async (
  intentId: string,
): Promise<DailyBriefDeliveryPacket> =>
  (
    await customFetch<Wrapped<DailyBriefDeliveryPacket>>(
      `/api/v1/ecom/finance/daily-brief-delivery-intents/${encodeURIComponent(
        intentId,
      )}/dispatch-packet`,
      { method: "GET" },
    )
  ).data;

export const fetchLatestDailyBriefCard = async (
  storeId: string,
): Promise<BriefCardSummary> =>
  (
    await customFetch<Wrapped<BriefCardSummary>>(
      `/api/v1/ecom/finance/daily-briefs/latest/card?${financeParams(storeId)}`,
      { method: "GET" },
    )
  ).data;

export function useLatestMetricSnapshot(storeId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "metric-snapshot", storeId],
    queryFn: () => fetchLatestMetricSnapshot(storeId as string),
    enabled: !!storeId,
    staleTime: 30_000,
  });
}

export function useMetricSnapshot(snapshotId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "metric-snapshot-detail", snapshotId],
    queryFn: () => fetchMetricSnapshot(snapshotId as string),
    enabled: !!snapshotId,
    staleTime: 30_000,
  });
}

export function useLatestMetricCard(
  storeId: string | null,
  currency?: string,
  metricName = "estimated_contribution_margin",
) {
  return useQuery({
    queryKey: ["ecom", "finance", "metric-card", storeId, metricName, currency],
    queryFn: () =>
      fetchLatestMetricCard(storeId as string, currency, metricName),
    enabled: !!storeId,
    staleTime: 30_000,
  });
}

export function useMetricCard(snapshotId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "metric-card-detail", snapshotId],
    queryFn: () => fetchMetricCard(snapshotId as string),
    enabled: !!snapshotId,
    staleTime: 30_000,
  });
}

export function useLatestDailyBrief(storeId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "daily-brief", storeId],
    queryFn: () => fetchLatestDailyBrief(storeId as string),
    enabled: !!storeId,
    staleTime: 30_000,
  });
}

export function useDailyBrief(briefId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "daily-brief-detail", briefId],
    queryFn: () => fetchDailyBrief(briefId as string),
    enabled: !!briefId,
    staleTime: 30_000,
  });
}

export function useDailyBriefDeliveryPacket(intentId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "daily-brief-delivery-packet", intentId],
    queryFn: () => fetchDailyBriefDeliveryPacket(intentId as string),
    enabled: !!intentId,
    staleTime: 30_000,
  });
}

export function useLatestDailyBriefCard(storeId: string | null) {
  return useQuery({
    queryKey: ["ecom", "finance", "daily-brief-card", storeId],
    queryFn: () => fetchLatestDailyBriefCard(storeId as string),
    enabled: !!storeId,
    staleTime: 30_000,
  });
}

// --- Vault (brand markdown docs) ---
export type VaultSummary = { slug: string; title: string; tags: string };
export type VaultDoc = VaultSummary & { body: string };

export const fetchVaultDocs = async (): Promise<VaultSummary[]> =>
  (
    await customFetch<Wrapped<VaultSummary[]>>("/api/v1/ecom/vault", {
      method: "GET",
    })
  ).data;

export const fetchVaultDoc = async (slug: string): Promise<VaultDoc> =>
  (
    await customFetch<Wrapped<VaultDoc>>(`/api/v1/ecom/vault/${slug}`, {
      method: "GET",
    })
  ).data;

export const saveVaultDoc = async (
  slug: string,
  payload: { title: string; tags: string; body: string },
): Promise<VaultDoc> =>
  (
    await customFetch<Wrapped<VaultDoc>>(`/api/v1/ecom/vault/${slug}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })
  ).data;

export function useVaultDocs() {
  return useQuery({
    queryKey: ["ecom", "vault"],
    queryFn: fetchVaultDocs,
    staleTime: 30_000,
  });
}

// --- Tickets / CS ---
export type Ticket = {
  id: string;
  subject: string;
  customer_email: string;
  customer_name: string;
  status: string;
  channel: string;
  created_at: string;
  updated_at: string;
};
export type TicketMessage = {
  direction: string;
  author: string;
  body: string;
  untrusted: boolean;
  created_at: string;
};
export type TicketEvidence = {
  kind: string;
  summary: string;
  created_at: string;
};
export type TicketDetail = Ticket & {
  messages: TicketMessage[];
  evidence: TicketEvidence[];
};

export const fetchTickets = async (): Promise<Ticket[]> =>
  (
    await customFetch<Wrapped<Ticket[]>>("/api/v1/ecom/tickets", {
      method: "GET",
    })
  ).data;

export const fetchTicket = async (id: string): Promise<TicketDetail> =>
  (
    await customFetch<Wrapped<TicketDetail>>(`/api/v1/ecom/tickets/${id}`, {
      method: "GET",
    })
  ).data;

export const runCsLoop = async (): Promise<{
  ingested: number;
  handled: number;
}> =>
  (
    await customFetch<Wrapped<{ ingested: number; handled: number }>>(
      "/api/v1/ecom/cs/run",
      { method: "POST", body: "{}" },
    )
  ).data;

export function useTickets() {
  // Live board: poll so new/changed tickets appear without a refresh.
  return useQuery({
    queryKey: ["ecom", "tickets"],
    queryFn: fetchTickets,
    staleTime: 4_000,
    refetchInterval: 8_000,
  });
}

export function useTicket(id: string | null) {
  // Live in-ticket feed: poll the open ticket so the agent's messages + evidence
  // stream in (faster while the agent is actively drafting).
  return useQuery({
    queryKey: ["ecom", "ticket", id],
    queryFn: () => fetchTicket(id as string),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data?.status === "auto_handling" ? 2_000 : 6_000,
  });
}

// --- Agents ---
export type AgentTemplate = {
  template: string;
  name: string;
  description: string;
  default_tools: string[];
};
export type AgentConfig = {
  id: string;
  template: string;
  name: string;
  voice: string;
  sops: string;
  allowed_tools: string[] | null;
  schedule: string;
  enabled: boolean;
};

export const fetchAgentTemplates = async (): Promise<AgentTemplate[]> =>
  (
    await customFetch<Wrapped<AgentTemplate[]>>(
      "/api/v1/ecom/agents/templates",
      { method: "GET" },
    )
  ).data;

export const fetchAgents = async (): Promise<AgentConfig[]> =>
  (
    await customFetch<Wrapped<AgentConfig[]>>("/api/v1/ecom/agents", {
      method: "GET",
    })
  ).data;

export const saveAgent = async (
  id: string,
  payload: { voice: string; sops: string; schedule: string; enabled: boolean },
): Promise<AgentConfig> =>
  (
    await customFetch<Wrapped<AgentConfig>>(`/api/v1/ecom/agents/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })
  ).data;

export function useAgents() {
  return useQuery({
    queryKey: ["ecom", "agents"],
    queryFn: fetchAgents,
    staleTime: 30_000,
  });
}

// --- Flows (configurable CS SOPs) ---
/** A branch on a step that waits for a customer reply: the LLM classifies the reply
 * against `label` and follows `goto` (a step id, or "resolve" / "escalate"). */
export type FlowBranch = { label: string; goto: string };
export type FlowStep = {
  id?: string;
  // "message" (LLM-generated email) | "request_refund_approval" | "resolve" | "escalate"
  // | legacy: lookup_order | cite_policy | send_reply | offer_discount
  type: string;
  prompt?: string; // the per-step LLM instruction (how to write this email)
  discount_percent?: number; // optional coupon issued with this step
  goto?: string; // next step when no branches: a step id | "resolve" | "escalate" | "next"
  branches?: FlowBranch[]; // present => wait for reply, classify, follow a branch
  // legacy fields (still accepted by the engine)
  message?: string;
  percent?: number;
  slug?: string;
  accept_message?: string;
  reason?: string;
};
export type Flow = {
  id: string;
  name: string;
  intent: string;
  enabled: boolean;
  triggers: string[] | null;
  escalate_keywords: string[] | null;
  steps: FlowStep[] | null;
};

export const fetchFlows = async (): Promise<Flow[]> =>
  (await customFetch<Wrapped<Flow[]>>("/api/v1/ecom/flows", { method: "GET" }))
    .data;

export const saveFlow = async (
  id: string,
  payload: {
    name: string;
    enabled: boolean;
    triggers: string[];
    escalate_keywords: string[];
    steps: FlowStep[];
  },
): Promise<Flow> =>
  (
    await customFetch<Wrapped<Flow>>(`/api/v1/ecom/flows/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })
  ).data;

export function useFlows() {
  return useQuery({
    queryKey: ["ecom", "flows"],
    queryFn: fetchFlows,
    staleTime: 30_000,
  });
}

// --- Insights ---
export type Insight = {
  kind: string;
  severity: string;
  title: string;
  detail: string;
};

export const fetchInsights = async (): Promise<Insight[]> =>
  (
    await customFetch<Wrapped<Insight[]>>("/api/v1/ecom/insights", {
      method: "GET",
    })
  ).data;

export function useInsights() {
  return useQuery({
    queryKey: ["ecom", "insights"],
    queryFn: fetchInsights,
    staleTime: 60_000,
  });
}

// --- Realtime (instant email handling) ---
export type Realtime = {
  enabled: boolean;
  webhook_url: string;
  detail?: string;
};

export const fetchRealtime = async (): Promise<Realtime> =>
  (
    await customFetch<Wrapped<Realtime>>("/api/v1/ecom/realtime", {
      method: "GET",
    })
  ).data;

export const enableRealtime = async (): Promise<Realtime> =>
  (
    await customFetch<Wrapped<Realtime>>("/api/v1/ecom/realtime/enable", {
      method: "POST",
      body: "{}",
    })
  ).data;

export function useRealtime() {
  return useQuery({
    queryKey: ["ecom", "realtime"],
    queryFn: fetchRealtime,
    staleTime: 30_000,
  });
}

// --- Team tasks (per-person Kanban) ---
export type TeamTask = {
  id: string;
  title: string;
  assignee: string;
  status: string;
};

export const fetchTeamTasks = async (): Promise<TeamTask[]> =>
  (
    await customFetch<Wrapped<TeamTask[]>>("/api/v1/ecom/tasks", {
      method: "GET",
    })
  ).data;

export const createTeamTask = async (
  title: string,
  assignee: string,
): Promise<TeamTask> =>
  (
    await customFetch<Wrapped<TeamTask>>("/api/v1/ecom/tasks", {
      method: "POST",
      body: JSON.stringify({ title, assignee }),
    })
  ).data;

export const updateTeamTask = async (
  id: string,
  patch: { status?: string; assignee?: string },
): Promise<TeamTask> =>
  (
    await customFetch<Wrapped<TeamTask>>(`/api/v1/ecom/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    })
  ).data;

export function useTeamTasks() {
  return useQuery({
    queryKey: ["ecom", "tasks"],
    queryFn: fetchTeamTasks,
    staleTime: 15_000,
  });
}

// --- Chat (read-only copilot) ---
export type ChatSource = { type: string; ref: string };
export type ChatResponse = { answer: string; sources: ChatSource[] };

export const sendChat = async (message: string): Promise<ChatResponse> =>
  (
    await customFetch<Wrapped<ChatResponse>>("/api/v1/ecom/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    })
  ).data;
export function useAgentTemplates() {
  return useQuery({
    queryKey: ["ecom", "agent-templates"],
    queryFn: fetchAgentTemplates,
    staleTime: 300_000,
  });
}

export function useStores() {
  return useQuery({
    queryKey: ["ecom", "stores"],
    queryFn: fetchStores,
    staleTime: 60_000,
  });
}

export function useConnections() {
  return useQuery({
    queryKey: ["ecom", "connections"],
    queryFn: fetchConnections,
    refetchInterval: 30_000,
  });
}

// --- Secrets (write-only: API never returns values, only set/not-set) ---
export type SecretStatus = { handle: string; set: boolean };

export const fetchSecrets = async (): Promise<SecretStatus[]> =>
  (
    await customFetch<Wrapped<SecretStatus[]>>(
      "/api/v1/ecom/settings/secrets",
      {
        method: "GET",
      },
    )
  ).data;

export const setSecret = async (
  handle: string,
  value: string,
): Promise<SecretStatus> =>
  (
    await customFetch<Wrapped<SecretStatus>>(
      `/api/v1/ecom/settings/secrets/${encodeURIComponent(handle)}`,
      { method: "PUT", body: JSON.stringify({ value }) },
    )
  ).data;

export const deleteSecret = async (handle: string): Promise<SecretStatus> =>
  (
    await customFetch<Wrapped<SecretStatus>>(
      `/api/v1/ecom/settings/secrets/${encodeURIComponent(handle)}`,
      { method: "DELETE" },
    )
  ).data;

export function useSecretsStatus() {
  return useQuery({
    queryKey: ["ecom", "secrets"],
    queryFn: fetchSecrets,
    staleTime: 30_000,
  });
}

// --- Stores management (add / set token / remove) ---
export const addStore = async (
  domain: string,
  name?: string,
): Promise<EcomStore> =>
  (
    await customFetch<Wrapped<EcomStore>>("/api/v1/ecom/stores", {
      method: "POST",
      body: JSON.stringify(name ? { domain, name } : { domain }),
    })
  ).data;

export const setStoreToken = async (
  id: string,
  value: string,
): Promise<EcomStore> =>
  (
    await customFetch<Wrapped<EcomStore>>(
      `/api/v1/ecom/stores/${encodeURIComponent(id)}/token`,
      { method: "PUT", body: JSON.stringify({ value }) },
    )
  ).data;

export const removeStore = async (id: string): Promise<{ removed: boolean }> =>
  (
    await customFetch<Wrapped<{ removed: boolean }>>(
      `/api/v1/ecom/stores/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    )
  ).data;

// --- Version / software ---
export type EcomVersion = { version: string; commit: string };

export const fetchVersion = async (): Promise<EcomVersion> =>
  (
    await customFetch<Wrapped<EcomVersion>>("/api/v1/ecom/version", {
      method: "GET",
    })
  ).data;

export function useVersion() {
  return useQuery({
    queryKey: ["ecom", "version"],
    queryFn: fetchVersion,
    staleTime: 300_000,
  });
}
