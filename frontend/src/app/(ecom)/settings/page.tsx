"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Check,
  CheckCircle2,
  Loader2,
  Plus,
  Store as StoreIcon,
  Trash2,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listContainer, listItem } from "@/lib/design/tokens";
import {
  addStore,
  deleteSecret,
  removeStore,
  setSecret,
  setStoreToken,
  useConnections,
  useSecretsStatus,
  useStores,
  useVersion,
  type EcomStore,
  type SecretStatus,
} from "@/lib/ecom-api";

/** Important secret handles surfaced to the operator. Values are write-only:
 * we render only "Set" / "Not set", never the secret itself. */
const SECRET_HANDLES: { handle: string; label: string; optional: boolean }[] = [
  { handle: "COMPOSIO_API_KEY", label: "Composio API key", optional: false },
  { handle: "ANTHROPIC_API_KEY", label: "Anthropic API key", optional: true },
  {
    handle: "SHOPIFY_REFUND_ACCESS_TOKEN",
    label: "Shopify refund access token",
    optional: true,
  },
];

function SetBadge({ set }: { set: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-1 text-xs font-medium",
        set
          ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
          : "bg-[color:var(--surface-muted)] text-muted",
      )}
    >
      {set ? "Set" : "Not set"}
    </span>
  );
}

const inputCls =
  "h-9 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 text-sm text-strong placeholder:text-quiet focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]";

function SecretRow({
  handle,
  label,
  optional,
  status,
}: {
  handle: string;
  label: string;
  optional: boolean;
  status?: SecretStatus;
}) {
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [saved, setSaved] = useState(false);
  const set = status?.set ?? false;

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["ecom", "secrets"] });

  const save = useMutation({
    mutationFn: () => setSecret(handle, value),
    onSuccess: () => {
      setValue("");
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
      invalidate();
    },
  });

  const clear = useMutation({
    mutationFn: () => deleteSecret(handle),
    onSuccess: invalidate,
  });

  return (
    <div className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center">
      <div className="min-w-0 sm:w-52">
        <p className="text-sm font-medium text-strong">
          {label}
          {optional ? (
            <span className="ml-1 text-xs font-normal text-quiet">(optional)</span>
          ) : null}
        </p>
        <p className="truncate text-xs text-quiet">{handle}</p>
      </div>
      <div className="flex items-center gap-2">
        <SetBadge set={set} />
      </div>
      <form
        className="flex flex-1 items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (value) save.mutate();
        }}
      >
        <input
          type="password"
          autoComplete="off"
          placeholder={set ? "Enter new value to replace" : "Enter value"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className={inputCls}
        />
        <Button type="submit" size="sm" disabled={!value || save.isPending}>
          {save.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : saved ? (
            <Check className="h-4 w-4" />
          ) : (
            "Save"
          )}
        </Button>
        {set ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={clear.isPending}
            onClick={() => clear.mutate()}
          >
            {clear.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Clear"
            )}
          </Button>
        ) : null}
      </form>
    </div>
  );
}

function StoreTokenForm({ store }: { store: EcomStore }) {
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [saved, setSaved] = useState(false);

  const save = useMutation({
    mutationFn: () => setStoreToken(store.id, value),
    onSuccess: () => {
      setValue("");
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
      qc.invalidateQueries({ queryKey: ["ecom", "stores"] });
      qc.invalidateQueries({ queryKey: ["ecom", "connections"] });
    },
  });

  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (value) save.mutate();
      }}
    >
      <input
        type="password"
        autoComplete="off"
        placeholder="Set Shopify token"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className={cn(inputCls, "h-8 w-44 text-xs")}
      />
      <Button type="submit" size="sm" disabled={!value || save.isPending}>
        {save.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : saved ? (
          <Check className="h-4 w-4" />
        ) : (
          "Save"
        )}
      </Button>
    </form>
  );
}

function AddStoreForm() {
  const qc = useQueryClient();
  const [domain, setDomain] = useState("");
  const [name, setName] = useState("");

  const add = useMutation({
    mutationFn: () => addStore(domain.trim(), name.trim() || undefined),
    onSuccess: () => {
      setDomain("");
      setName("");
      qc.invalidateQueries({ queryKey: ["ecom", "stores"] });
      qc.invalidateQueries({ queryKey: ["ecom", "connections"] });
    },
  });

  return (
    <form
      className="flex flex-col gap-2 sm:flex-row sm:items-center"
      onSubmit={(e) => {
        e.preventDefault();
        if (domain.trim()) add.mutate();
      }}
    >
      <input
        type="text"
        placeholder="my-store.myshopify.com"
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        className={inputCls}
      />
      <input
        type="text"
        placeholder="Display name (optional)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className={inputCls}
      />
      <Button type="submit" size="sm" disabled={!domain.trim() || add.isPending}>
        {add.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <>
            <Plus className="h-4 w-4" />
            Add store
          </>
        )}
      </Button>
    </form>
  );
}

function StoreRow({ store, first }: { store: EcomStore; first: boolean }) {
  const qc = useQueryClient();
  const remove = useMutation({
    mutationFn: () => removeStore(store.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ecom", "stores"] });
      qc.invalidateQueries({ queryKey: ["ecom", "connections"] });
    },
  });

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 px-4 py-3",
        !first && "border-t border-[color:var(--border)]",
      )}
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
        <StoreIcon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-strong">{store.name}</p>
        <p className="truncate text-xs text-quiet">{store.domain}</p>
      </div>
      <span
        className={cn(
          "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
          store.status === "connected"
            ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
            : "bg-[color:var(--surface-muted)] text-muted",
        )}
      >
        {store.status}
      </span>
      <StoreTokenForm store={store} />
      <Button
        type="button"
        size="sm"
        variant="ghost"
        aria-label="Remove store"
        disabled={remove.isPending}
        onClick={() => {
          if (
            window.confirm(
              `Remove ${store.name || store.domain}? This disconnects the store.`,
            )
          ) {
            remove.mutate();
          }
        }}
      >
        {remove.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Trash2 className="h-4 w-4 text-[color:var(--danger)]" />
        )}
      </Button>
    </div>
  );
}

export default function SettingsPage() {
  const connections = useConnections();
  const stores = useStores();
  const secrets = useSecretsStatus();
  const version = useVersion();

  const ready = connections.data?.ready ?? false;
  const secretsByHandle = new Map(
    (secrets.data ?? []).map((s) => [s.handle, s]),
  );

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Store connections, keys, stores, software"
      />

      {/* Connections (Build Spec §1.5) — provider status, never secrets. */}
      <section className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-[-0.01em] text-strong">
            Connections
          </h2>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium",
              ready
                ? "bg-[color:var(--success)]/10 text-[color:var(--success)]"
                : "bg-[color:var(--warning)]/10 text-[color:var(--warning)]",
            )}
          >
            {ready ? "CS loop ready" : "CS loop blocked"}
          </span>
        </div>
        <motion.div
          variants={listContainer}
          initial="hidden"
          animate="show"
          className="grid gap-3 sm:grid-cols-2"
        >
          {(connections.data?.providers ?? []).map((p) => (
            <motion.div
              key={p.provider}
              variants={listItem}
              className="flex items-center gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
            >
              {p.connected ? (
                <CheckCircle2 className="h-5 w-5 text-[color:var(--success)]" />
              ) : (
                <XCircle className="h-5 w-5 text-[color:var(--danger)]" />
              )}
              <div className="min-w-0">
                <p className="text-sm font-medium capitalize text-strong">
                  {p.provider}
                </p>
                <p className="truncate text-xs text-quiet">{p.detail}</p>
              </div>
            </motion.div>
          ))}
          {connections.isLoading ? (
            <div className="h-[68px] animate-pulse rounded-xl bg-[color:var(--surface-muted)]" />
          ) : null}
        </motion.div>
      </section>

      {/* API keys — write-only secrets. Show Set / Not set, never the value. */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold tracking-[-0.01em] text-strong">
          API keys
        </h2>
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card">
          {SECRET_HANDLES.map((s, i) => (
            <div
              key={s.handle}
              className={cn(i > 0 && "border-t border-[color:var(--border)]")}
            >
              <SecretRow
                handle={s.handle}
                label={s.label}
                optional={s.optional}
                status={secretsByHandle.get(s.handle)}
              />
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-quiet">
          Keys are write-only — once saved, values are never shown again. Enter a
          new value to replace, or Clear to remove.
        </p>
      </section>

      {/* Stores — live list + management. */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold tracking-[-0.01em] text-strong">
          Stores
        </h2>
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card">
          {(stores.data ?? []).map((s, i) => (
            <StoreRow key={s.id} store={s} first={i === 0} />
          ))}
          {!stores.isLoading && (stores.data ?? []).length === 0 ? (
            <p className="px-4 py-6 text-sm text-quiet">No stores connected yet.</p>
          ) : null}
          <div className="border-t border-[color:var(--border)] bg-[color:var(--surface-muted)]/40 px-4 py-3">
            <AddStoreForm />
          </div>
        </div>
        <p className="mt-2 text-xs text-quiet">
          Paste a Shopify Admin token for a direct connect, or let the agent
          connect a store via OAuth.
        </p>
      </section>

      {/* Software — version + self-update. */}
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold tracking-[-0.01em] text-strong">
          Software
        </h2>
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-strong">
                Version {version.data?.version ?? "—"}
              </p>
              <p className="mt-0.5 truncate font-mono text-xs text-quiet">
                {version.isLoading
                  ? "Loading…"
                  : (version.data?.commit ?? "unknown")}
              </p>
            </div>
            {version.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-quiet" />
            ) : null}
          </div>
          <p className="mt-3 text-xs text-muted">
            This deployment can self-update — the Hermes agent runs{" "}
            <code className="rounded bg-[color:var(--surface-muted)] px-1 py-0.5 font-mono text-[11px]">
              scripts/deploy/update.sh
            </code>{" "}
            to pull the latest, rebuild, and migrate.
          </p>
        </div>
      </section>
    </div>
  );
}
