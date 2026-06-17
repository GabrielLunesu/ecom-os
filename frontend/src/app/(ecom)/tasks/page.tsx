"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Plus } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { cn } from "@/lib/utils";
import { spring } from "@/lib/design/tokens";
import {
  createTeamTask,
  updateTeamTask,
  useTeamTasks,
  type TeamTask,
} from "@/lib/ecom-api";

const LANES = [
  { key: "todo", label: "To do" },
  { key: "doing", label: "In progress" },
  { key: "done", label: "Done" },
] as const;

const PALETTE = ["#4f46e5", "#0f9d58", "#d98a04", "#dc2626", "#0891b2"];

function avatar(name: string) {
  const initials = (name || "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const color = PALETTE[(name.charCodeAt(0) || 0) % PALETTE.length];
  return { initials, color };
}

export default function TasksPage() {
  const qc = useQueryClient();
  const tasks = useTeamTasks();
  const [dragId, setDragId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");

  const move = useMutation({
    mutationFn: (v: { id: string; status: string }) => updateTeamTask(v.id, { status: v.status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ecom", "tasks"] }),
  });
  const add = useMutation({
    mutationFn: () => createTeamTask(title.trim(), assignee.trim() || "Unassigned"),
    onSuccess: () => {
      setTitle("");
      setAssignee("");
      qc.invalidateQueries({ queryKey: ["ecom", "tasks"] });
    },
  });

  const all = tasks.data ?? [];

  return (
    <div>
      <PageHeader
        title="Tasks"
        subtitle="Per-person Kanban for the team"
        actions={
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (title.trim()) add.mutate();
            }}
            className="flex items-center gap-2"
          >
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="New task…"
              className="h-9 w-44 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 text-sm outline-none focus:border-[color:var(--accent)]"
            />
            <input
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              placeholder="Assignee"
              className="h-9 w-28 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 text-sm outline-none focus:border-[color:var(--accent)]"
            />
            <button
              type="submit"
              disabled={!title.trim() || add.isPending}
              className="flex h-9 items-center gap-1 rounded-lg bg-[color:var(--accent)] px-3 text-sm font-medium text-white disabled:opacity-50"
            >
              <Plus className="h-4 w-4" /> Add
            </button>
          </form>
        }
      />

      <div className="grid grid-cols-3 gap-3">
        {LANES.map((lane) => {
          const items = all.filter((t) => t.status === lane.key);
          return (
            <div
              key={lane.key}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => {
                if (dragId) move.mutate({ id: dragId, status: lane.key });
                setDragId(null);
              }}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-2.5"
            >
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="text-[13px] font-semibold text-strong">{lane.label}</span>
                <span className="rounded-full bg-[color:var(--surface)] px-2 text-xs text-muted">
                  {items.length}
                </span>
              </div>
              <div className="min-h-[120px] space-y-2">
                <AnimatePresence>
                  {items.map((t) => (
                    <TaskCard key={t.id} task={t} onDragStart={() => setDragId(t.id)} />
                  ))}
                </AnimatePresence>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({ task, onDragStart }: { task: TeamTask; onDragStart: () => void }) {
  const a = avatar(task.assignee);
  return (
    <motion.div
      layout
      layoutId={task.id}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={spring.default}
      draggable
      onDragStart={onDragStart}
      className={cn(
        "cursor-grab rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-3 shadow-card active:cursor-grabbing",
      )}
    >
      <p className="text-sm text-strong">{task.title}</p>
      <div className="mt-2 flex items-center gap-1.5">
        <span
          className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold text-white"
          style={{ backgroundColor: a.color }}
        >
          {a.initials}
        </span>
        <span className="text-xs text-quiet">{task.assignee}</span>
      </div>
    </motion.div>
  );
}
