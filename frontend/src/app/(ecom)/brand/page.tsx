"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { Check, FileText, Loader2 } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fetchVaultDoc, saveVaultDoc, useVaultDocs } from "@/lib/ecom-api";

export default function BrandPage() {
  const qc = useQueryClient();
  const docs = useVaultDocs();
  const [slug, setSlug] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [body, setBody] = useState("");

  // Default to the first document once the list loads.
  useEffect(() => {
    if (!slug && docs.data && docs.data.length > 0) setSlug(docs.data[0].slug);
  }, [slug, docs.data]);

  const doc = useQuery({
    queryKey: ["ecom", "vault", slug],
    queryFn: () => fetchVaultDoc(slug as string),
    enabled: !!slug,
  });

  useEffect(() => {
    if (doc.data) {
      setTitle(doc.data.title);
      setTags(doc.data.tags);
      setBody(doc.data.body);
    }
  }, [doc.data]);

  const save = useMutation({
    mutationFn: () => saveVaultDoc(slug as string, { title, tags, body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ecom", "vault"] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Brand"
        subtitle="Markdown vault the agents read (shipping & privacy policy, SOPs)"
      />
      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        {/* Document list */}
        <div className="space-y-1">
          {(docs.data ?? []).map((d) => (
            <button
              key={d.slug}
              type="button"
              onClick={() => setSlug(d.slug)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                slug === d.slug
                  ? "bg-[color:var(--accent-soft)] text-[color:var(--accent)]"
                  : "text-muted hover:bg-[color:var(--surface-muted)]",
              )}
            >
              <FileText className="h-4 w-4 shrink-0" />
              <span className="truncate">{d.title}</span>
            </button>
          ))}
        </div>

        {/* Editor + live preview */}
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title"
              className="w-full bg-transparent text-lg font-semibold tracking-[-0.01em] text-strong outline-none"
            />
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="tags, comma, separated"
              className="mt-1 w-full bg-transparent text-xs text-quiet outline-none"
            />
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              spellCheck={false}
              className="mt-3 h-[420px] w-full resize-none rounded-lg bg-[color:var(--surface-muted)] p-3 font-mono text-[13px] leading-relaxed text-strong outline-none"
            />
            <div className="mt-3 flex items-center gap-3">
              <Button
                size="sm"
                onClick={() => save.mutate()}
                disabled={save.isPending || !slug}
              >
                {save.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : save.isSuccess ? (
                  <Check className="h-4 w-4" />
                ) : null}
                Save to vault
              </Button>
              {save.isSuccess ? (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xs text-[color:var(--success)]"
                >
                  Saved
                </motion.span>
              ) : null}
            </div>
          </div>

          <div className="prose prose-sm max-w-none rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
