"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Plus, Send, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import {
  addOperatorTaskComment,
  createAskHermesIntent,
  createOperatorTask,
  updateOperatorTask,
  useOperatorTasks,
  type AskHermesLaunchIntent,
  type OperatorTaskCreate,
  type OperatorTask,
} from "@/lib/ecom-api";
import { cn } from "@/lib/utils";

const STATUSES: OperatorTask["status"][] = ["todo", "doing", "blocked", "done"];
const PRIORITIES: OperatorTask["priority"][] = [
  "low",
  "normal",
  "high",
  "urgent",
];
const ROLES = ["viewer", "operator", "cs_rep", "finance", "owner"] as const;
const ACCESS_LABELS = [
  "public",
  "operations",
  "cs",
  "finance",
  "founder_private",
] as const;

function formatDate(value: string | null) {
  if (!value) return "No due date";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function dateInputValue(value: string | null) {
  return value ? value.slice(0, 10) : "";
}

export default function TasksPage() {
  const qc = useQueryClient();
  const [role, setRole] = useState<(typeof ROLES)[number]>("operator");
  const tasks = useOperatorTasks(role);
  const all = useMemo(() => tasks.data ?? [], [tasks.data]);
  const [view, setView] = useState<"board" | "list">("board");
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");
  const [priority, setPriority] = useState<OperatorTask["priority"]>("normal");
  const [accessLabel, setAccessLabel] =
    useState<(typeof ACCESS_LABELS)[number]>("operations");
  const [dailyBriefInclude, setDailyBriefInclude] = useState(true);
  const [due, setDue] = useState("");
  const [entityType, setEntityType] = useState("");
  const [entityId, setEntityId] = useState("");
  const [commentByTask, setCommentByTask] = useState<Record<string, string>>(
    {},
  );
  const [intentByTask, setIntentByTask] = useState<
    Record<string, AskHermesLaunchIntent>
  >({});

  const invalidate = () =>
    qc.invalidateQueries({
      queryKey: ["ecom", "operator-workspace", "tasks"],
    });

  const create = useMutation({
    mutationFn: () =>
      createOperatorTask({
        title: title.trim(),
        assignee_type: assignee.trim() ? "external" : "unassigned",
        assignee_label: assignee.trim(),
        priority,
        access_label: accessLabel,
        daily_brief_include: dailyBriefInclude,
        due_at: due ? new Date(`${due}T12:00:00`).toISOString() : null,
        provenance: "human",
        entity_links:
          entityType.trim() && entityId.trim()
            ? [{ entity_type: entityType.trim(), entity_id: entityId.trim() }]
            : [],
      }),
    onSuccess: () => {
      setTitle("");
      setAssignee("");
      setPriority("normal");
      setAccessLabel("operations");
      setDailyBriefInclude(true);
      setDue("");
      setEntityType("");
      setEntityId("");
      invalidate();
    },
  });

  const update = useMutation({
    mutationFn: (payload: { id: string; patch: Partial<OperatorTaskCreate> }) =>
      updateOperatorTask(payload.id, payload.patch, role),
    onSuccess: invalidate,
  });

  const comment = useMutation({
    mutationFn: (payload: { id: string; body: string }) =>
      addOperatorTaskComment(payload.id, payload.body, role),
    onSuccess: (_data, variables) => {
      setCommentByTask((current) => ({ ...current, [variables.id]: "" }));
      invalidate();
    },
  });

  const askHermes = useMutation({
    mutationFn: (task: OperatorTask) =>
      createAskHermesIntent({
        surface: "tasks",
        entity_refs: [
          {
            entity_type: "task",
            entity_id: task.id,
            label: task.title,
            trace_id: task.source_trace_id,
          },
          ...task.entity_links.map((link) => ({
            entity_type: link.entity_type,
            entity_id: link.entity_id,
            label: link.label,
            trace_id: link.trace_id,
          })),
        ],
        trace_id: task.source_trace_id,
        suggested_prompt: `Inspect task ${task.title}`,
        access_label: "operations",
      }),
    onSuccess: (intent, task) => {
      setIntentByTask((current) => ({
        ...current,
        [task.id]: intent,
      }));
    },
  });

  const grouped = useMemo(() => {
    const next = new Map<OperatorTask["status"], OperatorTask[]>();
    for (const status of STATUSES) next.set(status, []);
    for (const task of all) {
      const bucket = next.get(task.status) ?? [];
      bucket.push(task);
      next.set(task.status, bucket);
    }
    return next;
  }, [all]);

  return (
    <div>
      <PageHeader
        title="Tasks"
        subtitle="Operator tasks with provenance, due dates, entity links, and comments"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={role}
              onChange={(event) =>
                setRole(event.target.value as (typeof ROLES)[number])
              }
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            >
              {ROLES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <div className="inline-flex rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-1">
              {(["board", "list"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setView(mode)}
                  className={cn(
                    "h-8 rounded-md px-3 text-sm font-medium capitalize",
                    view === mode
                      ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                      : "text-muted",
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
        }
      />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (title.trim()) create.mutate();
        }}
        className="mb-5 grid gap-2 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-3 shadow-card md:grid-cols-[1.3fr_0.8fr_0.6fr_0.8fr_0.7fr_0.6fr_0.7fr_0.5fr_auto]"
      >
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Task title"
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <input
          value={assignee}
          onChange={(event) => setAssignee(event.target.value)}
          placeholder="Assignee"
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <select
          value={priority}
          onChange={(event) =>
            setPriority(event.target.value as OperatorTask["priority"])
          }
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        >
          {PRIORITIES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select
          value={accessLabel}
          onChange={(event) =>
            setAccessLabel(event.target.value as (typeof ACCESS_LABELS)[number])
          }
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        >
          {ACCESS_LABELS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={due}
          onChange={(event) => setDue(event.target.value)}
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <input
          value={entityType}
          onChange={(event) => setEntityType(event.target.value)}
          placeholder="Entity"
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <input
          value={entityId}
          onChange={(event) => setEntityId(event.target.value)}
          placeholder="Entity ID"
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <label className="flex h-10 items-center gap-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-muted">
          <input
            type="checkbox"
            checked={dailyBriefInclude}
            onChange={(event) => setDailyBriefInclude(event.target.checked)}
            className="h-4 w-4"
          />
          Brief
        </label>
        <Button
          type="submit"
          size="sm"
          disabled={!title.trim() || create.isPending}
        >
          <Plus className="h-4 w-4" />
          Add
        </Button>
      </form>

      {tasks.isLoading ? (
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          Loading tasks…
        </div>
      ) : tasks.isError ? (
        <div className="rounded-xl border border-[color:var(--danger)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          Tasks are unavailable.
        </div>
      ) : all.length === 0 ? (
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          No operator tasks found.
        </div>
      ) : view === "board" ? (
        <div className="grid gap-3 lg:grid-cols-4">
          {STATUSES.map((status) => (
            <section
              key={status}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-3"
            >
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold capitalize text-strong">
                  {status}
                </h2>
                <span className="text-xs tabular-nums text-muted">
                  {grouped.get(status)?.length ?? 0}
                </span>
              </div>
              <div className="space-y-2">
                {(grouped.get(status) ?? []).map((task) => (
                  <TaskPanel
                    key={task.id}
                    task={task}
                    commentValue={commentByTask[task.id] ?? ""}
                    launchIntent={intentByTask[task.id]}
                    onCommentChange={(value) =>
                      setCommentByTask((current) => ({
                        ...current,
                        [task.id]: value,
                      }))
                    }
                    onCommentSubmit={() => {
                      const body = commentByTask[task.id]?.trim();
                      if (body) comment.mutate({ id: task.id, body });
                    }}
                    onAskHermes={() => askHermes.mutate(task)}
                    onPatch={(patch) =>
                      update.mutate({
                        id: task.id,
                        patch,
                      })
                    }
                    onStatus={(nextStatus) =>
                      update.mutate({
                        id: task.id,
                        patch: { status: nextStatus },
                      })
                    }
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-[color:var(--surface-muted)] text-xs text-muted">
              <tr>
                <th className="px-4 py-3">Task</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Due</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Provenance</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {all.map((task) => (
                <tr
                  key={task.id}
                  className="border-t border-[color:var(--border)]"
                >
                  <td className="px-4 py-3 font-medium text-strong">
                    {task.title}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {task.assignee_label || "Unassigned"}
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {formatDate(task.due_at)}
                  </td>
                  <td className="px-4 py-3 text-muted">{task.priority}</td>
                  <td className="px-4 py-3 text-muted">{task.provenance}</td>
                  <td className="px-4 py-3 text-muted">{task.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TaskPanel({
  task,
  commentValue,
  launchIntent,
  onCommentChange,
  onCommentSubmit,
  onAskHermes,
  onPatch,
  onStatus,
}: {
  task: OperatorTask;
  commentValue: string;
  launchIntent?: AskHermesLaunchIntent;
  onCommentChange: (value: string) => void;
  onCommentSubmit: () => void;
  onAskHermes: () => void;
  onPatch: (patch: Partial<OperatorTaskCreate>) => void;
  onStatus: (status: OperatorTask["status"]) => void;
}) {
  return (
    <article className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-3 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-strong">{task.title}</h3>
          <p className="mt-1 text-xs text-muted">
            {task.assignee_label || "Unassigned"} · {formatDate(task.due_at)}
          </p>
        </div>
        <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
          {task.priority}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {task.entity_links.map((link) => (
          <span
            key={`${link.entity_type}:${link.entity_id}`}
            className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-[11px] text-muted"
          >
            {link.entity_type}: {link.label || link.entity_id}
          </span>
        ))}
        <span className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-[11px] text-muted">
          {task.provenance}
        </span>
        {task.source_trace_id ? (
          <span className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-[11px] text-muted">
            trace linked
          </span>
        ) : null}
        <span className="rounded bg-[color:var(--surface-muted)] px-2 py-1 text-[11px] text-muted">
          {task.access_label}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {STATUSES.filter((status) => status !== task.status).map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => onStatus(status)}
            className="rounded-lg border border-[color:var(--border)] px-2 py-1 text-[11px] text-muted hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
          >
            {status}
          </button>
        ))}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-1.5">
        <input
          key={`${task.id}:${task.assignee_label}`}
          defaultValue={task.assignee_label}
          onBlur={(event) => {
            const nextAssignee = event.target.value.trim();
            if (nextAssignee !== task.assignee_label) {
              onPatch({
                assignee_type: nextAssignee ? "external" : "unassigned",
                assignee_label: nextAssignee,
              });
            }
          }}
          placeholder="Assignee"
          className="h-8 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-muted outline-none focus:border-[color:var(--accent)]"
        />
        <select
          value={task.priority}
          onChange={(event) =>
            onPatch({
              priority: event.target.value as OperatorTask["priority"],
            })
          }
          className="h-8 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-muted outline-none focus:border-[color:var(--accent)]"
        >
          {PRIORITIES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={dateInputValue(task.due_at)}
          onChange={(event) =>
            onPatch({
              due_at: event.target.value
                ? new Date(`${event.target.value}T12:00:00`).toISOString()
                : null,
            })
          }
          className="h-8 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-muted outline-none focus:border-[color:var(--accent)]"
        />
        <select
          value={task.access_label}
          onChange={(event) =>
            onPatch({
              access_label: event.target.value as OperatorTask["access_label"],
            })
          }
          className="h-8 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-muted outline-none focus:border-[color:var(--accent)]"
        >
          {ACCESS_LABELS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <label className="flex h-8 items-center gap-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={task.daily_brief_include}
            onChange={(event) =>
              onPatch({ daily_brief_include: event.target.checked })
            }
            className="h-3.5 w-3.5"
          />
          Brief
        </label>
      </div>

      {task.comments.length ? (
        <div className="mt-3 space-y-1">
          {task.comments.slice(-2).map((comment) => (
            <p key={comment.id} className="text-xs text-quiet">
              {comment.body}
            </p>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <input
          value={commentValue}
          onChange={(event) => onCommentChange(event.target.value)}
          placeholder="Comment"
          className="h-8 min-w-0 flex-1 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-2 text-xs text-strong outline-none focus:border-[color:var(--accent)]"
        />
        <button
          type="button"
          onClick={onCommentSubmit}
          disabled={!commentValue.trim()}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--border)] text-muted disabled:opacity-50"
          title="Add comment"
        >
          <MessageSquarePlus className="h-3.5 w-3.5" />
        </button>
      </div>

      <button
        type="button"
        onClick={onAskHermes}
        className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-[color:var(--accent)]"
      >
        <Sparkles className="h-3.5 w-3.5" />
        Prepare Hermes
        {launchIntent ? <Send className="h-3.5 w-3.5" /> : null}
      </button>
      {launchIntent ? (
        <p className="mt-1 text-[11px] text-quiet">
          Intent ready · {launchIntent.entity_refs.length} refs · TTL{" "}
          {launchIntent.ttl_seconds}s
        </p>
      ) : null}
    </article>
  );
}
