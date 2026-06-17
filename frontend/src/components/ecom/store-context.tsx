"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * Global store-scope state for the whole app: the active Shopify store, or the
 * "All stores" aggregate. One brand, many stores (Build Spec §1). Every data
 * surface reads `activeStoreId` to scope its queries.
 *
 * Slice 1 seeds a static list; Slice 2 replaces `useSeedStores()` with the
 * backend stores endpoint (Composio/connection refs). The shape stays the same.
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

// Seed list until Slice 2 wires the backend stores endpoint.
const SEED_STORES: Store[] = [
  { id: "chicago-outlet", name: "Chicago Outlet", domain: "stv0xe-c4.myshopify.com" },
];

function readInitial(): StoreScope {
  if (typeof window === "undefined") return ALL_STORES;
  return window.localStorage.getItem(STORAGE_KEY) ?? ALL_STORES;
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [stores] = useState<Store[]>(SEED_STORES);
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
