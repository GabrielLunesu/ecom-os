"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, Check, Loader2, ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listContainer, listItem } from "@/lib/design/tokens";
import {
  saveAgent,
  useAgents,
  useAgentTemplates,
  type AgentConfig,
} from "@/lib/ecom-api";

export default function AgentsPage() {
  const templates = useAgentTemplates();
  const agents = useAgents();
  const cs = agents.data?.find((a) => a.template === "cs") ?? agents.data?.[0] ?? null;

  return (
    <div>
      <PageHeader
        title="Agents"
        subtitle="Create from templates; configure voice, SOPs, allowed tools, schedule"
      />

      <motion.div
        variants={listContainer}
        initial="hidden"
        animate="show"
        className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4"
      >
        {(templates.data ?? []).map((t) => (
          <motion.div
            key={t.template}
            variants={listItem}
            whileHover={{ y: -2 }}
            className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
              <Bot className="h-4 w-4" />
            </div>
            <p className="mt-2.5 text-sm font-semibold text-strong">{t.name}</p>
            <p className="mt-0.5 text-xs text-quiet">{t.description}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {t.default_tools.map((tool) => (
                <span
                  key={tool}
                  className="rounded bg-[color:var(--surface-muted)] px-1.5 py-0.5 text-[10px] text-muted"
                >
                  {tool}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </motion.div>

      {cs ? <AgentEditor agent={cs} /> : null}
    </div>
  );
}

function AgentEditor({ agent }: { agent: AgentConfig }) {
  const qc = useQueryClient();
  const [voice, setVoice] = useState(agent.voice);
  const [sops, setSops] = useState(agent.sops);
  const [schedule, setSchedule] = useState(agent.schedule);
  const [enabled, setEnabled] = useState(agent.enabled);

  useEffect(() => {
    setVoice(agent.voice);
    setSops(agent.sops);
    setSchedule(agent.schedule);
    setEnabled(agent.enabled);
  }, [agent]);

  const save = useMutation({
    mutationFn: () => saveAgent(agent.id, { voice, sops, schedule, enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ecom", "agents"] }),
  });

  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-5 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-strong">{agent.name}</p>
          <p className="text-xs text-quiet capitalize">{agent.template} template</p>
        </div>
        <button
          type="button"
          onClick={() => setEnabled((v) => !v)}
          className={cn(
            "relative h-6 w-11 rounded-full transition-colors",
            enabled ? "bg-[color:var(--accent)]" : "bg-[color:var(--surface-strong)]",
          )}
        >
          <motion.span
            layout
            className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm"
            style={{ left: enabled ? 22 : 2 }}
          />
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-muted">Voice</label>
          <textarea
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
            className="mt-1 h-20 w-full resize-none rounded-lg bg-[color:var(--surface-muted)] p-2.5 text-sm text-strong outline-none"
          />
          <label className="mt-3 block text-xs font-medium text-muted">SOPs</label>
          <textarea
            value={sops}
            onChange={(e) => setSops(e.target.value)}
            className="mt-1 h-28 w-full resize-none rounded-lg bg-[color:var(--surface-muted)] p-2.5 text-sm text-strong outline-none"
          />
          <label className="mt-3 block text-xs font-medium text-muted">Schedule</label>
          <input
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
            className="mt-1 w-full rounded-lg bg-[color:var(--surface-muted)] p-2.5 text-sm text-strong outline-none"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted">Allowed tools</label>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {(agent.allowed_tools ?? []).map((t) => (
              <span
                key={t}
                className="rounded bg-[color:var(--surface-muted)] px-2 py-0.5 text-xs text-muted"
              >
                {t}
              </span>
            ))}
          </div>
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-[color:var(--accent-soft)] p-3 text-xs text-[color:var(--accent)]">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Capability is bound by the connector layer: this agent has read + discount
              tools only. No refund tool exists to grant (Invariant 2).
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : save.isSuccess ? (
            <Check className="h-4 w-4" />
          ) : null}
          Save configuration
        </Button>
      </div>
    </div>
  );
}
