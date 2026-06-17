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
