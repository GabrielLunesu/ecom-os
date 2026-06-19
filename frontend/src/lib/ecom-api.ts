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

// --- A07 operator workspace ---
export type EntityLink = {
  id?: string;
  entity_type: string;
  entity_id: string;
  label?: string;
  trace_id?: string | null;
};

export type OperatorTask = {
  id: string;
  brand_id: string;
  title: string;
  description: string | null;
  status: "todo" | "doing" | "blocked" | "done" | "cancelled";
  priority: "low" | "normal" | "high" | "urgent";
  due_at: string | null;
  assignee_type: "unassigned" | "user" | "hermes_profile" | "external";
  assignee_id: string | null;
  assignee_label: string;
  provenance: "human" | "agent";
  created_by_actor_type: string;
  created_by_actor_id: string | null;
  source_trace_id: string | null;
  source_run_id: string | null;
  source_evidence_ref: string | null;
  access_label: KnowledgeDocumentSearchResult["access_label"];
  daily_brief_include: boolean;
  entity_links: EntityLink[];
  comments: Array<{
    id: string;
    body: string;
    actor_type: string;
    actor_id: string | null;
    trace_id: string | null;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
};

export type OperatorTaskCreate = {
  title: string;
  description?: string | null;
  status?: OperatorTask["status"];
  priority?: OperatorTask["priority"];
  due_at?: string | null;
  assignee_type?: OperatorTask["assignee_type"];
  assignee_label?: string;
  provenance?: OperatorTask["provenance"];
  access_label?: OperatorTask["access_label"];
  daily_brief_include?: boolean;
  entity_links?: EntityLink[];
};

export type KnowledgeDocumentSearchResult = {
  document_id: string;
  version_id: string;
  title: string;
  logical_path: string;
  source: string;
  effective_date: string | null;
  access_label: "public" | "operations" | "cs" | "finance" | "founder_private";
  trust_label: "operator_supplied" | "imported" | "verified" | "untrusted";
  supersession_state: "current" | "superseded";
  snippet: string | null;
  evidence_ref: string;
  ingestion_status: string;
  extraction_status: string;
};

export type KnowledgeDocument = KnowledgeDocumentSearchResult & {
  body: string;
  version_number: number;
  supersedes_version_id: string | null;
  checksum: string;
  created_at: string;
};

export type KnowledgeSearchResponse = {
  role: string;
  query: string;
  accessible_count: number;
  results: KnowledgeDocumentSearchResult[];
};

export type KnowledgeDocumentUpsert = {
  logical_path: string;
  title: string;
  body: string;
  document_type?: string;
  source?: string;
  access_label?: KnowledgeDocumentSearchResult["access_label"];
  trust_label?: KnowledgeDocumentSearchResult["trust_label"];
  effective_date?: string | null;
};

export type AttentionInput = {
  kind: string;
  id: string;
  title: string;
  summary?: string;
  severity?: "critical" | "high" | "medium" | "low" | "info";
  source_status?: "available" | "partial" | "stale" | "unavailable";
  coverage?: "verified" | "observed" | "imported" | "unknown";
  trace_id?: string | null;
  source_refs?: AttentionSourceRef[];
  freshness_as_of?: string | null;
  primary_action?: string | null;
  reasons?: string[];
};

export type AttentionSourceRef = {
  type: string;
  id: string;
  label?: string;
};

export const todaySourceHref = (
  source: AttentionSourceRef,
  fallback?: string | null,
): string | null => {
  switch (source.type) {
    case "task":
      return "/tasks";
    case "ticket":
      return "/cs";
    case "connection":
      return "/settings";
    case "metric":
      return "/analytics";
    case "insight":
      return "/overview";
    case "document":
    case "document_version":
      return "/knowledge";
    case "dependency":
      return null;
    default:
      return fallback ?? null;
  }
};

export const todayTraceHref = (traceId?: string | null): string | null =>
  traceId ? `/activity?trace=${encodeURIComponent(traceId)}` : null;

export const todayUnavailableDependencies = (
  item: Pick<AttentionItem, "unavailable_dependencies">,
): string[] =>
  item.unavailable_dependencies
    .map((dependency) => dependency.trim())
    .filter(Boolean);

export const todayFreshnessLabel = (value?: string | null): string | null => {
  if (!value) return null;
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(timestamp);
};

export type AttentionItem = Required<
  Pick<
    AttentionInput,
    | "kind"
    | "id"
    | "title"
    | "severity"
    | "source_status"
    | "coverage"
    | "reasons"
  >
> &
  Omit<
    AttentionInput,
    "severity" | "source_status" | "coverage" | "reasons"
  > & {
    rank: number;
    score: number;
    unavailable_dependencies: string[];
  };

export type AttentionSnapshot = {
  id: string;
  brand_id: string;
  status: string;
  source_status: AttentionInput["source_status"];
  window_start: string | null;
  window_end: string | null;
  input_count: number;
  item_count: number;
  inputs: AttentionInput[];
  items: AttentionItem[];
  created_at: string;
};

export type AskHermesLaunchIntent = {
  surface: string;
  entity_refs: EntityLink[];
  trace_id: string | null;
  suggested_prompt: string;
  access_label: KnowledgeDocumentSearchResult["access_label"];
  ttl_seconds: number;
};

type Settled<T> = PromiseSettledResult<T>;

const isFulfilled = <T>(
  result: Settled<T>,
): result is PromiseFulfilledResult<T> => result.status === "fulfilled";

const unavailableAttention = (
  kind: string,
  title: string,
  summary: string,
): AttentionInput => ({
  kind,
  id: `${kind}:unavailable`,
  title,
  summary,
  severity: "medium",
  source_status: "unavailable",
  coverage: "unknown",
  reasons: ["source unavailable"],
  source_refs: [{ type: "dependency", id: kind, label: "Unavailable" }],
});

export const buildTodayAttentionInputs = ({
  tasks,
  connections,
  metrics,
  tickets,
  insights,
}: {
  tasks: Settled<OperatorTask[]>;
  connections: Settled<Connections>;
  metrics: Settled<Metrics>;
  tickets: Settled<Ticket[]>;
  insights: Settled<Insight[]>;
}): AttentionInput[] => {
  const inputs: AttentionInput[] = [
    unavailableAttention(
      "approvals",
      "Approvals source unavailable",
      "A05 approval source contract is not registered in this branch.",
    ),
    unavailableAttention(
      "incidents",
      "Incident source unavailable",
      "A02 incident source contract is not registered in this branch.",
    ),
    unavailableAttention(
      "failed_unknown_actions",
      "Action outcome source unavailable",
      "A02 action state source contract is not registered in this branch.",
    ),
    unavailableAttention(
      "briefs",
      "Brief source unavailable",
      "A08 daily brief source contract is not registered in this branch.",
    ),
  ];

  if (isFulfilled(tasks)) {
    const now = Date.now();
    const due = tasks.value.filter((task) => {
      if (
        task.status === "done" ||
        task.status === "cancelled" ||
        !task.due_at
      ) {
        return false;
      }
      return new Date(task.due_at).getTime() <= now + 24 * 60 * 60 * 1000;
    });
    if (due.length > 0) {
      inputs.push({
        kind: "due_tasks",
        id: "due_tasks",
        title: `${due.length} task${due.length === 1 ? "" : "s"} due soon`,
        summary: due.map((task) => task.title).join(", "),
        severity: due.some((task) => task.priority === "urgent")
          ? "high"
          : "medium",
        source_status: "available",
        coverage: "verified",
        trace_id:
          due.find((task) => task.source_trace_id)?.source_trace_id ?? null,
        source_refs: due.slice(0, 5).map((task) => ({
          type: "task",
          id: task.id,
          label: task.title,
        })),
        reasons: ["due within 24 hours", "task source available"],
        primary_action: "/tasks",
      });
    }
  } else {
    inputs.push(
      unavailableAttention(
        "due_tasks",
        "Task source unavailable",
        "Tasks are not counted as zero because the source request failed.",
      ),
    );
  }

  if (isFulfilled(connections)) {
    const unhealthy = connections.value.providers.filter(
      (provider) => !provider.connected,
    );
    if (!connections.value.ready || unhealthy.length > 0) {
      inputs.push({
        kind: "health",
        id: "connections",
        title: "Connection health needs attention",
        summary: unhealthy
          .map((provider) => `${provider.provider}: ${provider.detail}`)
          .join("; "),
        severity: "high",
        source_status: "partial",
        coverage: "verified",
        source_refs: unhealthy.map((provider) => ({
          type: "connection",
          id: provider.provider,
          label: provider.detail,
        })),
        reasons: ["one or more providers are disconnected"],
        primary_action: "/settings",
      });
    }
  } else {
    inputs.push(
      unavailableAttention(
        "health",
        "Health source unavailable",
        "Connection health is unavailable and is not treated as healthy.",
      ),
    );
  }

  if (isFulfilled(tickets)) {
    const needsRep = tickets.value.filter(
      (ticket) => ticket.status === "needs_rep",
    );
    const open = tickets.value.filter((ticket) => ticket.status !== "resolved");
    if (needsRep.length > 0 || open.length > 5) {
      inputs.push({
        kind: "cs_backlog",
        id: "cs_backlog",
        title: needsRep.length
          ? `${needsRep.length} ticket${needsRep.length === 1 ? "" : "s"} need a representative`
          : `${open.length} open tickets`,
        summary: needsRep
          .slice(0, 3)
          .map((ticket) => ticket.subject)
          .join(", "),
        severity: needsRep.length ? "high" : "medium",
        source_status: "available",
        coverage: "verified",
        source_refs: [...needsRep, ...open].slice(0, 5).map((ticket) => ({
          type: "ticket",
          id: ticket.id,
          label: ticket.subject,
        })),
        reasons: needsRep.length
          ? ["sticky escalation tickets require human attention"]
          : ["open ticket backlog above local threshold"],
        primary_action: "/cs",
      });
    }
  } else {
    inputs.push(
      unavailableAttention(
        "cs_backlog",
        "CS backlog source unavailable",
        "Backlog is unavailable and is not counted as zero.",
      ),
    );
  }

  if (isFulfilled(metrics)) {
    inputs.push({
      kind: "metrics",
      id: "metrics:legacy",
      title: "Metric source available",
      summary: `Revenue source returned ${metrics.value.kpis.currency} ${metrics.value.kpis.revenue.toFixed(2)} for its selected window.`,
      severity: Object.keys(metrics.value.unavailable).length ? "low" : "info",
      source_status: Object.keys(metrics.value.unavailable).length
        ? "partial"
        : "available",
      coverage: "imported",
      source_refs: [
        {
          type: "metric",
          id: "legacy:ecom_metrics",
          label: metrics.value.scope,
        },
      ],
      reasons: [
        "legacy metric endpoint responded",
        "A08 metric snapshot contract pending",
      ],
      primary_action: "/analytics",
    });
  } else {
    inputs.push(
      unavailableAttention(
        "metrics",
        "Metric source unavailable",
        "Metrics are unavailable and are not treated as zero.",
      ),
    );
  }

  if (isFulfilled(insights)) {
    for (const insight of insights.value.filter(
      (item) => item.severity === "warning",
    )) {
      inputs.push({
        kind: "insight",
        id: `${insight.kind}:${insight.title}`,
        title: insight.title,
        summary: insight.detail,
        severity: "medium",
        source_status: "available",
        coverage: "observed",
        source_refs: [
          { type: "insight", id: insight.kind, label: insight.title },
        ],
        reasons: ["insight severity is warning"],
        primary_action: "/overview",
      });
    }
  }

  return inputs;
};

export const fetchOperatorTasks = async (
  role = "operator",
): Promise<OperatorTask[]> =>
  (
    await customFetch<Wrapped<OperatorTask[]>>(
      `/api/v1/ecom/operator-workspace/tasks?role=${encodeURIComponent(role)}`,
      { method: "GET" },
    )
  ).data;

export const createOperatorTask = async (
  payload: OperatorTaskCreate,
): Promise<OperatorTask> =>
  (
    await customFetch<Wrapped<OperatorTask>>(
      "/api/v1/ecom/operator-workspace/tasks",
      { method: "POST", body: JSON.stringify(payload) },
    )
  ).data;

export const updateOperatorTask = async (
  id: string,
  patch: Partial<OperatorTaskCreate>,
  role = "operator",
): Promise<OperatorTask> =>
  (
    await customFetch<Wrapped<OperatorTask>>(
      `/api/v1/ecom/operator-workspace/tasks/${id}?role=${encodeURIComponent(role)}`,
      { method: "PATCH", body: JSON.stringify(patch) },
    )
  ).data;

export const addOperatorTaskComment = async (
  id: string,
  body: string,
  role = "operator",
): Promise<OperatorTask["comments"][number]> =>
  (
    await customFetch<Wrapped<OperatorTask["comments"][number]>>(
      `/api/v1/ecom/operator-workspace/tasks/${id}/comments?role=${encodeURIComponent(role)}`,
      { method: "POST", body: JSON.stringify({ body }) },
    )
  ).data;

export const searchKnowledge = async (
  query: string,
  role: string,
): Promise<KnowledgeSearchResponse> =>
  (
    await customFetch<Wrapped<KnowledgeSearchResponse>>(
      `/api/v1/ecom/operator-workspace/knowledge/search?query=${encodeURIComponent(query)}&role=${encodeURIComponent(role)}`,
      { method: "GET" },
    )
  ).data;

export const roleTestKnowledge = async (
  query: string,
  role: string,
): Promise<KnowledgeSearchResponse> =>
  (
    await customFetch<Wrapped<KnowledgeSearchResponse>>(
      "/api/v1/ecom/operator-workspace/knowledge/role-test",
      { method: "POST", body: JSON.stringify({ query, role }) },
    )
  ).data;

export const upsertKnowledgeDocument = async (
  payload: KnowledgeDocumentUpsert,
): Promise<KnowledgeDocument> =>
  (
    await customFetch<Wrapped<KnowledgeDocument>>(
      "/api/v1/ecom/operator-workspace/knowledge/documents",
      { method: "POST", body: JSON.stringify(payload) },
    )
  ).data;

export const fetchKnowledgeDocument = async (
  documentId: string,
  role: string,
  versionId?: string | null,
): Promise<KnowledgeDocument> => {
  const params = new URLSearchParams({ role });
  if (versionId) params.set("version_id", versionId);
  return (
    await customFetch<Wrapped<KnowledgeDocument>>(
      `/api/v1/ecom/operator-workspace/knowledge/documents/${encodeURIComponent(documentId)}?${params.toString()}`,
      { method: "GET" },
    )
  ).data;
};

export const rankAttention = async (
  inputs: AttentionInput[],
): Promise<AttentionItem[]> =>
  (
    await customFetch<Wrapped<AttentionItem[]>>(
      "/api/v1/ecom/operator-workspace/attention/rank",
      { method: "POST", body: JSON.stringify(inputs) },
    )
  ).data;

export const createAttentionSnapshot = async (payload: {
  inputs: AttentionInput[];
  window_start?: string | null;
  window_end?: string | null;
}): Promise<AttentionSnapshot> =>
  (
    await customFetch<Wrapped<AttentionSnapshot>>(
      "/api/v1/ecom/operator-workspace/attention/snapshots",
      { method: "POST", body: JSON.stringify(payload) },
    )
  ).data;

export const createAskHermesIntent = async (payload: {
  surface: string;
  entity_refs: EntityLink[];
  trace_id?: string | null;
  suggested_prompt: string;
  access_label?: KnowledgeDocumentSearchResult["access_label"];
}): Promise<AskHermesLaunchIntent> =>
  (
    await customFetch<Wrapped<AskHermesLaunchIntent>>(
      "/api/v1/ecom/operator-workspace/ask-hermes-intents",
      { method: "POST", body: JSON.stringify(payload) },
    )
  ).data;

export const fetchTodayAttention = async (): Promise<AttentionSnapshot> => {
  const fetchedAt = Date.now();
  const [tasks, connections, metrics, tickets, insights] =
    await Promise.allSettled([
      fetchOperatorTasks(),
      fetchConnections(),
      fetchMetrics("all", 1),
      fetchTickets(),
      fetchInsights(),
    ]);
  const inputs = buildTodayAttentionInputs({
    tasks,
    connections,
    metrics,
    tickets,
    insights,
  });

  return createAttentionSnapshot({
    inputs,
    window_start: new Date(fetchedAt - 24 * 60 * 60 * 1000).toISOString(),
    window_end: new Date(fetchedAt).toISOString(),
  });
};

export function useOperatorTasks(role = "operator") {
  return useQuery({
    queryKey: ["ecom", "operator-workspace", "tasks", role],
    queryFn: () => fetchOperatorTasks(role),
    staleTime: 15_000,
  });
}

export function useKnowledgeSearch(query: string, role: string) {
  return useQuery({
    queryKey: ["ecom", "operator-workspace", "knowledge", query, role],
    queryFn: () => roleTestKnowledge(query, role),
    staleTime: 15_000,
  });
}

export function useTodayAttention() {
  return useQuery({
    queryKey: ["ecom", "operator-workspace", "today"],
    queryFn: fetchTodayAttention,
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
