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

export const fetchStores = () =>
  customFetch<EcomStore[]>("/api/v1/ecom/stores", { method: "GET" });

export const fetchConnections = () =>
  customFetch<Connections>("/api/v1/ecom/connections", { method: "GET" });

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
