"use client";

import { useEffect, useState } from "react";
import { BookOpen, FileText, Loader2, Search, Sparkles, Trash2, UploadCloud } from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";
import { Textarea } from "@/ui/primitives/textarea";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import { ApiError, knowledgeApi } from "@/platform/api";
import { UnansweredTopics } from "@/domains/customer-service/automation/UnansweredTopics";

type KBDocRow = {
  doc_id: string;
  updated_at?: string;
  chunks?: number;
};

type KBResult = {
  id: number;
  doc_id: string;
  chunk_index?: number | null;
  content: string;
  score_hybrid?: number;
};

function formatDate(value?: string) {
  if (!value) return "—";

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof ApiError) return `${fallback}: ${err.status} ${err.body}`;
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
}

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KBDocRow[]>([]);
  const [results, setResults] = useState<KBResult[]>([]);

  const [docId, setDocId] = useState("refund-policy");
  const [text, setText] = useState("Refund Policy: returns accepted within 5 days.");
  const [query, setQuery] = useState("refund policy");

  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [activeDeleteId, setActiveDeleteId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function loadDocs() {
    try {
      setIsLoadingDocs(true);
      setStatus(null);

      const data: any = await knowledgeApi.docs();
      setDocs(data.docs || []);
    } catch (err) {
      setStatus(errorMessage(err, "Could not load knowledge docs"));
    } finally {
      setIsLoadingDocs(false);
    }
  }

  async function ingest() {
    const texts = text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    if (texts.length === 0) {
      setStatus("Add at least one knowledge paragraph before ingesting.");
      return;
    }

    try {
      setIsIngesting(true);
      setStatus(null);

      const data: any = await knowledgeApi.ingest({
        doc_id: docId || undefined,
        texts,
      });

      setStatus(`Ingested ${data.chunks ?? texts.length} chunks into ${data.doc_id ?? docId}.`);
      await loadDocs();
    } catch (err) {
      setStatus(errorMessage(err, "Could not ingest knowledge"));
    } finally {
      setIsIngesting(false);
    }
  }

  async function search() {
    if (!query.trim()) {
      setStatus("Enter a query before searching.");
      return;
    }

    try {
      setIsSearching(true);
      setStatus(null);
      setResults([]);

      const data: any = await knowledgeApi.search({
        query,
        top_k: 5,
      });

      setResults(data.results || []);
      setStatus(`Found ${(data.results || []).length} relevant chunks.`);
    } catch (err) {
      setStatus(errorMessage(err, "Could not search knowledge"));
    } finally {
      setIsSearching(false);
    }
  }

  async function deleteDoc(doc_id: string) {
    try {
      setActiveDeleteId(doc_id);
      setStatus(null);

      await knowledgeApi.deleteDoc(doc_id);
      setDocs((current) => current.filter((doc) => doc.doc_id !== doc_id));
      setResults((current) => current.filter((result) => result.doc_id !== doc_id));
      setStatus(`Deleted ${doc_id}.`);
    } catch (err) {
      setStatus(errorMessage(err, "Could not delete doc"));
    } finally {
      setActiveDeleteId(null);
    }
  }

  useEffect(() => {
    loadDocs().catch(() => {});
  }, []);

  return (
    <AppContainer>
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge Base"
        description="Manage policies, FAQs, product docs, macros, and support knowledge used by AI replies and workflows."
      />

      {status && (
        <ProductNotice>{status}</ProductNotice>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <ProductStatCard label="Documents" value={docs.length} icon={BookOpen} />
        <ProductStatCard
          label="Chunks"
          value={docs.reduce((total, doc) => total + (doc.chunks ?? 0), 0)}
          icon={FileText}
        />
        <ProductStatCard label="AI ready" value={docs.length > 0 ? "Yes" : "No"} icon={Sparkles} />
      </div>

      <UnansweredTopics title="Questions your help articles don't answer" />

      <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <ProductPanel
          title="Add knowledge"
          description="Paste policies, FAQs, shipping rules, refund rules, or product notes. Each line becomes searchable context."
        >
          <div className="space-y-3">
            <Input
              value={docId}
              onChange={(event) => setDocId(event.target.value)}
              placeholder="Document ID, e.g. refund-policy"
            />

            <Textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              className="min-h-48"
              placeholder="Paste knowledge here..."
            />

            <Button
              onClick={ingest}
              disabled={isIngesting}
              className="w-full gap-2"
            >
              {isIngesting ? <Loader2 className="animate-spin" size={15} /> : <UploadCloud size={15} />}
              Ingest knowledge
            </Button>
          </div>
        </ProductPanel>

        <div className="space-y-6">
          <ProductPanel
            title="Search knowledge"
            description="Test what the AI reply engine can retrieve before it answers customers."
          >
            <div className="flex flex-col gap-3 md:flex-row">
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") search().catch(() => {});
                }}
                className="min-w-0 flex-1"
                placeholder="Search refund policy, damaged item, shipping delay..."
              />

              <Button
                onClick={search}
                disabled={isSearching}
                className="gap-2"
              >
                {isSearching ? <Loader2 className="animate-spin" size={15} /> : <Search size={15} />}
                Search
              </Button>
            </div>

            <div className="mt-5 space-y-3">
              {results.length === 0 ? (
                <ProductNotice>No search results yet.</ProductNotice>
              ) : (
                results.map((result) => (
                  <div key={result.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs font-medium text-slate-500">
                        {result.doc_id} · chunk {result.chunk_index ?? 0}
                      </div>
                      <div className="text-xs text-slate-400">
                        {typeof result.score_hybrid === "number"
                          ? `score ${result.score_hybrid.toFixed(3)}`
                          : "hybrid"}
                      </div>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-700">
                      {result.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          </ProductPanel>

          <ProductPanel
            title="Knowledge sources"
            description="These documents power AI reply composition, suggested actions, and workflow decisions."
          >
            {isLoadingDocs ? (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="animate-spin" size={16} />
                Loading docs...
              </div>
            ) : docs.length === 0 ? (
              <ProductNotice>No knowledge sources connected yet.</ProductNotice>
            ) : (
              <div className="space-y-3">
                {docs.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-slate-950">{doc.doc_id}</div>
                      <div className="mt-1 text-sm text-slate-500">
                        {doc.chunks ?? 0} chunks · updated {formatDate(doc.updated_at)}
                      </div>
                    </div>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => deleteDoc(doc.doc_id)}
                      disabled={activeDeleteId !== null}
                      className="gap-2"
                    >
                      {activeDeleteId === doc.doc_id ? (
                        <Loader2 className="animate-spin" size={14} />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </ProductPanel>
        </div>
      </div>
    </AppContainer>
  );
}
