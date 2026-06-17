"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { useStores } from "@/lib/ecom-api";

/**
 * Global store-scope state for the whole app: the active Shopify store, or the
 * "All stores" aggregate. One brand, many stores (Build Spec §1). Every data
 * surface reads `activeStoreId` to scope its queries. Stores come from the
 * backend `/ecom/stores` endpoint (connection refs only).
 */
export type Store = {
  id: string;
  name: string;
  domain: string;
};

export const ALL_STORES = "all" as const;
export type StoreScope = typeof ALL_STORES | string;

type StoreContextValue = {
  stores: Store[];
  activeStoreId: StoreScope;
  setActiveStoreId: (id: StoreScope) => void;
  activeStore: Store | null; // null when aggregate is selected
  isAggregate: boolean;
};

const StoreContext = createContext<StoreContextValue | null>(null);

const STORAGE_KEY = "ecom_active_store";

function readInitial(): StoreScope {
  if (typeof window === "undefined") return ALL_STORES;
  return window.localStorage.getItem(STORAGE_KEY) ?? ALL_STORES;
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const { data } = useStores();
  const stores: Store[] = useMemo(
    () =>
      (data ?? []).map((s) => ({ id: s.id, name: s.name, domain: s.domain })),
    [data],
  );
  const [activeStoreId, setActiveStoreIdState] = useState<StoreScope>(readInitial);

  const setActiveStoreId = useCallback((id: StoreScope) => {
    setActiveStoreIdState(id);
    if (typeof window !== "undefined") window.localStorage.setItem(STORAGE_KEY, id);
  }, []);

  const value = useMemo<StoreContextValue>(() => {
    const isAggregate = activeStoreId === ALL_STORES;
    return {
      stores,
      activeStoreId,
      setActiveStoreId,
      isAggregate,
      activeStore: isAggregate
        ? null
        : (stores.find((s) => s.id === activeStoreId) ?? null),
    };
  }, [stores, activeStoreId, setActiveStoreId]);

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used within <StoreProvider>");
  return ctx;
}
