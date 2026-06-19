"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Search, Send, Sparkles } from "lucide-react";

import { PageHeader } from "@/components/ecom/PageHeader";
import { Button } from "@/components/ui/button";
import {
  createAskHermesIntent,
  fetchKnowledgeDocument,
  upsertKnowledgeDocument,
  useKnowledgeSearch,
  type AskHermesLaunchIntent,
  type KnowledgeDocument,
  type KnowledgeDocumentSearchResult,
} from "@/lib/ecom-api";

const ACCESS_LABELS = [
  "public",
  "operations",
  "cs",
  "finance",
  "founder_private",
] as const;
const TRUST_LABELS = [
  "operator_supplied",
  "imported",
  "verified",
  "untrusted",
] as const;
const DOCUMENT_TYPES = ["markdown", "text", "html"] as const;
const ROLES = ["viewer", "operator", "cs_rep", "finance", "owner"] as const;

export default function KnowledgePage() {
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<(typeof ROLES)[number]>("operator");
  const [logicalPath, setLogicalPath] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [source, setSource] = useState("operator");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [documentType, setDocumentType] =
    useState<(typeof DOCUMENT_TYPES)[number]>("markdown");
  const [accessLabel, setAccessLabel] =
    useState<(typeof ACCESS_LABELS)[number]>("operations");
  const [trustLabel, setTrustLabel] =
    useState<(typeof TRUST_LABELS)[number]>("operator_supplied");
  const [intentByDoc, setIntentByDoc] = useState<
    Record<string, AskHermesLaunchIntent>
  >({});
  const [documentByVersion, setDocumentByVersion] = useState<
    Record<string, KnowledgeDocument>
  >({});
  const search = useKnowledgeSearch(query, role);

  const save = useMutation({
    mutationFn: () =>
      upsertKnowledgeDocument({
        logical_path: logicalPath.trim(),
        title: title.trim(),
        body,
        access_label: accessLabel,
        trust_label: trustLabel,
        source: source.trim() || "operator",
        document_type: documentType,
        effective_date: effectiveDate || null,
      }),
    onSuccess: () => {
      setLogicalPath("");
      setTitle("");
      setBody("");
      setSource("operator");
      setEffectiveDate("");
      setDocumentType("markdown");
      qc.invalidateQueries({
        queryKey: ["ecom", "operator-workspace", "knowledge"],
      });
    },
  });

  const askHermes = useMutation({
    mutationFn: (doc: KnowledgeDocumentSearchResult) =>
      createAskHermesIntent({
        surface: "knowledge",
        entity_refs: [
          {
            entity_type: "document",
            entity_id: doc.document_id,
            label: doc.title,
          },
          {
            entity_type: "document_version",
            entity_id: doc.version_id,
            label: doc.supersession_state,
          },
        ],
        suggested_prompt: `Inspect document ${doc.title}`,
        access_label: doc.access_label,
      }),
    onSuccess: (intent, doc) => {
      setIntentByDoc((current) => ({
        ...current,
        [doc.version_id]: intent,
      }));
    },
  });

  const openDocument = useMutation({
    mutationFn: (doc: KnowledgeDocumentSearchResult) =>
      fetchKnowledgeDocument(doc.document_id, role, doc.version_id),
    onSuccess: (document) => {
      setDocumentByVersion((current) => ({
        ...current,
        [document.version_id]: document,
      }));
    },
  });

  const results = search.data?.results ?? [];

  return (
    <div>
      <PageHeader
        title="Knowledge"
        subtitle="Versioned documents with role-tested retrieval and source labels"
      />

      <div className="mb-5 grid gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-3 shadow-card lg:grid-cols-[1fr_180px_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search documents"
            className="h-10 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] pl-9 pr-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
          />
        </div>
        <select
          value={role}
          onChange={(event) =>
            setRole(event.target.value as (typeof ROLES)[number])
          }
          className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        >
          {ROLES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <div className="flex items-center rounded-lg border border-[color:var(--border)] px-3 text-sm text-muted">
          {search.data?.accessible_count ?? 0} accessible
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (logicalPath.trim() && title.trim()) save.mutate();
        }}
        className="mb-5 grid gap-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-3 shadow-card lg:grid-cols-2"
      >
        <div className="space-y-2">
          <input
            value={logicalPath}
            onChange={(event) => setLogicalPath(event.target.value)}
            placeholder="Logical path"
            className="h-10 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
          />
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Title"
            className="h-10 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
          />
          <div className="grid grid-cols-3 gap-2">
            <input
              value={source}
              onChange={(event) => setSource(event.target.value)}
              placeholder="Source"
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            />
            <input
              type="date"
              value={effectiveDate}
              onChange={(event) => setEffectiveDate(event.target.value)}
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            />
            <select
              value={documentType}
              onChange={(event) =>
                setDocumentType(
                  event.target.value as (typeof DOCUMENT_TYPES)[number],
                )
              }
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            >
              {DOCUMENT_TYPES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={accessLabel}
              onChange={(event) =>
                setAccessLabel(
                  event.target.value as (typeof ACCESS_LABELS)[number],
                )
              }
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            >
              {ACCESS_LABELS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <select
              value={trustLabel}
              onChange={(event) =>
                setTrustLabel(
                  event.target.value as (typeof TRUST_LABELS)[number],
                )
              }
              className="h-10 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 text-sm text-strong outline-none focus:border-[color:var(--accent)]"
            >
              {TRUST_LABELS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <Button
            type="submit"
            size="sm"
            disabled={!logicalPath.trim() || !title.trim() || save.isPending}
          >
            <Plus className="h-4 w-4" />
            Save version
          </Button>
        </div>
        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Document body"
          className="min-h-48 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-3 font-mono text-sm text-strong outline-none focus:border-[color:var(--accent)]"
        />
      </form>

      {search.isLoading ? (
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          Loading documents…
        </div>
      ) : search.isError ? (
        <div className="rounded-xl border border-[color:var(--danger)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          Knowledge retrieval is unavailable.
        </div>
      ) : results.length === 0 ? (
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-6 text-sm text-muted shadow-card">
          No accessible documents matched this role and query.
        </div>
      ) : (
        <div className="space-y-3">
          {results.map((doc) => (
            <article
              key={doc.version_id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 shadow-card"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <FileText className="h-4 w-4 text-muted" />
                    <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                      {doc.access_label}
                    </span>
                    <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                      {doc.trust_label}
                    </span>
                    <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 text-[11px] text-muted">
                      {doc.supersession_state}
                    </span>
                  </div>
                  <h2 className="mt-2 text-base font-semibold text-strong">
                    {doc.title}
                  </h2>
                  <p className="mt-1 text-xs text-muted">{doc.logical_path}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openDocument.mutate(doc)}
                    className="inline-flex h-9 items-center gap-2 rounded-xl border border-[color:var(--border)] px-3 text-sm font-medium text-strong hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
                  >
                    <FileText className="h-4 w-4" />
                    Open version
                  </button>
                  <button
                    type="button"
                    onClick={() => askHermes.mutate(doc)}
                    className="inline-flex h-9 items-center gap-2 rounded-xl border border-[color:var(--border)] px-3 text-sm font-medium text-strong hover:border-[color:var(--accent)] hover:text-[color:var(--accent)]"
                  >
                    <Sparkles className="h-4 w-4" />
                    Prepare Hermes
                    {intentByDoc[doc.version_id] ? (
                      <Send className="h-4 w-4" />
                    ) : null}
                  </button>
                </div>
              </div>
              {intentByDoc[doc.version_id] ? (
                <p className="mt-2 text-[11px] text-quiet">
                  Intent ready ·{" "}
                  {intentByDoc[doc.version_id].entity_refs.length} refs · TTL{" "}
                  {intentByDoc[doc.version_id].ttl_seconds}s
                </p>
              ) : null}
              {doc.snippet ? (
                <p className="mt-3 text-sm text-muted">{doc.snippet}</p>
              ) : null}
              {documentByVersion[doc.version_id] ? (
                <div className="mt-3 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-muted)] p-3">
                  <div className="flex flex-wrap gap-2 text-[11px] text-quiet">
                    <span>
                      v{documentByVersion[doc.version_id].version_number}
                    </span>
                    <span>{documentByVersion[doc.version_id].checksum}</span>
                    <span>
                      created {documentByVersion[doc.version_id].created_at}
                    </span>
                    {documentByVersion[doc.version_id].supersedes_version_id ? (
                      <span>
                        supersedes{" "}
                        {
                          documentByVersion[doc.version_id]
                            .supersedes_version_id
                        }
                      </span>
                    ) : null}
                  </div>
                  <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-xs text-muted">
                    {documentByVersion[doc.version_id].body}
                  </pre>
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-1.5 text-xs text-quiet">
                <span>{doc.source}</span>
                <span>{doc.ingestion_status}</span>
                <span>{doc.extraction_status}</span>
                <span>{doc.evidence_ref}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
