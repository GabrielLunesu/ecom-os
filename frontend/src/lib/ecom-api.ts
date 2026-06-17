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
};

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
  (await customFetch<Wrapped<EcomStore[]>>("/api/v1/ecom/stores", { method: "GET" }))
    .data;

export const fetchConnections = async (): Promise<Connections> =>
  (await customFetch<Wrapped<Connections>>("/api/v1/ecom/connections", { method: "GET" }))
    .data;

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

export const fetchMetrics = async (store: string, days: number): Promise<Metrics> =>
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
  (await customFetch<Wrapped<VaultSummary[]>>("/api/v1/ecom/vault", { method: "GET" }))
    .data;

export const fetchVaultDoc = async (slug: string): Promise<VaultDoc> =>
  (
    await customFetch<Wrapped<VaultDoc>>(`/api/v1/ecom/vault/${slug}`, { method: "GET" })
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
export type TicketEvidence = { kind: string; summary: string; created_at: string };
export type TicketDetail = Ticket & {
  messages: TicketMessage[];
  evidence: TicketEvidence[];
};

export const fetchTickets = async (): Promise<Ticket[]> =>
  (await customFetch<Wrapped<Ticket[]>>("/api/v1/ecom/tickets", { method: "GET" })).data;

export const fetchTicket = async (id: string): Promise<TicketDetail> =>
  (await customFetch<Wrapped<TicketDetail>>(`/api/v1/ecom/tickets/${id}`, { method: "GET" }))
    .data;

export const runCsLoop = async (): Promise<{ ingested: number; handled: number }> =>
  (await customFetch<Wrapped<{ ingested: number; handled: number }>>(
    "/api/v1/ecom/cs/run",
    { method: "POST", body: "{}" },
  )).data;

export function useTickets() {
  return useQuery({ queryKey: ["ecom", "tickets"], queryFn: fetchTickets, staleTime: 10_000 });
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
  (await customFetch<Wrapped<AgentTemplate[]>>("/api/v1/ecom/agents/templates", { method: "GET" }))
    .data;

export const fetchAgents = async (): Promise<AgentConfig[]> =>
  (await customFetch<Wrapped<AgentConfig[]>>("/api/v1/ecom/agents", { method: "GET" })).data;

export const saveAgent = async (
  id: string,
  payload: { voice: string; sops: string; schedule: string; enabled: boolean },
): Promise<AgentConfig> =>
  (await customFetch<Wrapped<AgentConfig>>(`/api/v1/ecom/agents/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })).data;

export function useAgents() {
  return useQuery({ queryKey: ["ecom", "agents"], queryFn: fetchAgents, staleTime: 30_000 });
}

// --- Chat (read-only copilot) ---
export type ChatSource = { type: string; ref: string };
export type ChatResponse = { answer: string; sources: ChatSource[] };

export const sendChat = async (message: string): Promise<ChatResponse> =>
  (await customFetch<Wrapped<ChatResponse>>("/api/v1/ecom/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  })).data;
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
