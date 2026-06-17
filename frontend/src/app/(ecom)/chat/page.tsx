"use client";

import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Bot, Loader2, User } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { cn } from "@/lib/utils";
import { spring } from "@/lib/design/tokens";
import { sendChat, type ChatSource } from "@/lib/ecom-api";

type Msg = { role: "user" | "assistant"; text: string; sources?: ChatSource[] };

const SUGGESTIONS = ["order #1001", "revenue last 30 days", "shipping policy"];

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: (q: string) => sendChat(q),
    onSuccess: (res) => {
      setMessages((m) => [...m, { role: "assistant", text: res.answer, sources: res.sources }]);
      queueMicrotask(() => scroller.current?.scrollTo({ top: 9e9, behavior: "smooth" }));
    },
  });

  const submit = (q: string) => {
    const text = q.trim();
    if (!text || ask.isPending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    ask.mutate(text);
    queueMicrotask(() => scroller.current?.scrollTo({ top: 9e9, behavior: "smooth" }));
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <PageHeader title="Chat" subtitle="Read-only copilot over Shopify + the vault" />

      <div
        ref={scroller}
        className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
              <Bot className="h-5 w-5" />
            </div>
            <p className="text-sm text-muted">
              Ask about orders, KPIs, or brand policies. Read-only — I never make changes.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-[color:var(--border)] px-3 py-1 text-xs text-muted hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={spring.default}
              className={cn("flex gap-2.5", m.role === "user" ? "justify-end" : "justify-start")}
            >
              {m.role === "assistant" ? (
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
                  <Bot className="h-4 w-4" />
                </div>
              ) : null}
              <div
                className={cn(
                  "max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm",
                  m.role === "user"
                    ? "bg-[color:var(--accent)] text-white"
                    : "bg-[color:var(--surface-muted)] text-strong",
                )}
              >
                <p className="whitespace-pre-wrap">{m.text}</p>
                {m.sources && m.sources.length > 0 ? (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {m.sources.map((s, j) => (
                      <span
                        key={j}
                        className="rounded bg-[color:var(--surface)] px-1.5 py-0.5 text-[10px] text-muted"
                      >
                        {s.type}: {s.ref}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              {m.role === "user" ? (
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[color:var(--surface-strong)] text-muted">
                  <User className="h-4 w-4" />
                </div>
              ) : null}
            </motion.div>
          ))}
        </AnimatePresence>
        {ask.isPending ? (
          <div className="flex items-center gap-2 text-sm text-quiet">
            <Loader2 className="h-4 w-4 animate-spin" /> thinking…
          </div>
        ) : null}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className="mt-3 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about orders, KPIs, or policies…"
          className="flex-1 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-2.5 text-sm text-strong shadow-card outline-none focus:border-[color:var(--accent)]"
        />
        <button
          type="submit"
          disabled={!input.trim() || ask.isPending}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-[color:var(--accent)] text-white disabled:opacity-50"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
