"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, Trash2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { cn } from "@/platform/utils";
import { Button } from "@/ui/primitives/button";

import { ToneChip } from "../inbox/case/parts";
import { WorkflowGraph } from "./WorkflowGraph";
import { StepSettings } from "./StepSettings";
import { studioApi, type LibraryItem, type RawWorkflow, type WorkflowDetail } from "./api";
import { FIXED_NODE_TYPES, countChanges, insertOnEdge, nodeLabel, removeNode, toGraph, updateNodeData } from "./graphEdits";

const GROUPS: { key: LibraryItem["group"]; label: string }[] = [
  { key: "agents", label: "Agents" },
  { key: "tools", label: "Tools" },
  { key: "logic", label: "Logic" },
];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[11.5px] font-semibold uppercase tracking-wide text-text-secondary">{children}</h2>;
}

export default function WorkflowEditorScreen({ workflowId }: { workflowId: string }) {
  const router = useRouter();
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [library, setLibrary] = useState<LibraryItem[]>([]);
  const [draft, setDraft] = useState<RawWorkflow | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [insertEdge, setInsertEdge] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([studioApi.workflow(workflowId), studioApi.nodeLibrary()])
      .then(([workflow, items]) => {
        setDetail(workflow);
        setDraft(workflow.workflow);
        setLibrary(items);
      })
      .catch((err) => setError(apiErrorMessage(err, "Could not load this workflow.")));
  }, [workflowId]);

  const graph = useMemo(() => (draft ? toGraph(draft, library) : null), [draft, library]);
  const changes = useMemo(() => (detail && draft ? countChanges(detail.workflow, draft) : null), [detail, draft]);
  const libraryByType = useMemo(() => new Map(library.map((item) => [item.node_type, item])), [library]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setInsertEdge(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (error && !draft) return <p role="alert" className="p-6 text-[13.5px] text-danger">{error}</p>;
  if (!detail || !draft || !graph) {
    return (
      <p className="flex items-center gap-2 p-6 text-[13.5px] text-text-secondary">
        <Loader2 size={15} className="animate-spin" aria-hidden /> Loading workflow…
      </p>
    );
  }

  const selectedNode = draft.nodes.find((n) => n.id === selected) ?? null;
  const insertAt = insertEdge !== null ? draft.edges[insertEdge] : null;
  const labelOf = (id: string) => {
    const node = draft.nodes.find((n) => n.id === id);
    return node ? nodeLabel(node) : id;
  };

  const addStep = (item: LibraryItem) => {
    if (insertEdge === null) return;
    const result = insertOnEdge(draft, insertEdge, item);
    setDraft(result.workflow);
    setSelected(result.id);
    setInsertEdge(null);
  };

  const review = async () => {
    setSaving(true);
    setError(null);
    try {
      const proposal = await studioApi.proposeGraphEdit(detail.id, draft);
      router.push(`/app/workflows/proposals/${proposal.id}`);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not create the proposed change."));
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface px-4 py-2.5">
        <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-[13.5px]">
          <Link href="/app/workflows" className="text-text-secondary hover:text-foreground">Workflows</Link>
          <span className="text-text-secondary">/</span>
          <span className="truncate text-text-secondary">{detail.name}</span>
          <span className="text-text-secondary">/</span>
          <span className="font-semibold text-foreground">Edit steps</span>
          {detail.live_version ? <ToneChip tone="neutral" className="ml-1">Editing from live v{detail.live_version}</ToneChip> : null}
        </nav>
        <div className="flex items-center gap-3">
          {changes?.total ? (
            <span className="hidden font-mono text-[12px] tabular-nums text-text-secondary md:inline">
              {changes.added} new · {changes.changed} changed · {changes.removed} removed
            </span>
          ) : null}
          <Button variant="secondary" size="sm" disabled={saving} onClick={() => router.push("/app/workflows")}>Cancel</Button>
          <Button size="sm" disabled={saving || !changes?.total} onClick={() => void review()}>
            {saving ? "Preparing…" : "Review changes"}
          </Button>
        </div>
      </div>

      {detail.open_proposal_id ? (
        <p className="border-b border-border bg-warning/5 px-4 py-2 text-[12.5px] text-foreground">
          Another proposed change to this workflow is waiting.{" "}
          <Link href={`/app/workflows/proposals/${detail.open_proposal_id}`} className="font-medium text-primary hover:underline">
            Review it
          </Link>{" "}
          or keep editing. Your edits become a separate proposal.
        </p>
      ) : null}

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-y-auto lg:grid-cols-[260px_minmax(0,1fr)_340px] lg:overflow-hidden">
        {/* Left: node library */}
        <aside className="min-h-0 overflow-y-auto border-b border-border bg-surface p-4 lg:border-b-0 lg:border-r" aria-label="Step library">
          <SectionLabel>Add a step</SectionLabel>
          <p className={cn("mt-2 rounded-control px-2.5 py-2 text-[12.5px] leading-5", insertAt ? "bg-primary/[0.07] text-foreground" : "bg-muted text-text-secondary")}>
            {insertAt
              ? <>Adding between <strong className="font-semibold">{labelOf(insertAt.source)}</strong> and <strong className="font-semibold">{labelOf(insertAt.target)}</strong>. Pick a step.</>
              : "Click + on a line in the graph to choose where the new step goes."}
          </p>
          {GROUPS.map((group) => {
            const items = library.filter((item) => item.group === group.key);
            if (!items.length) return null;
            return (
              <div key={group.key} className="mt-4">
                <h3 className="text-[12.5px] font-semibold text-foreground">{group.label}</h3>
                <ul className="mt-1.5 space-y-1">
                  {items.map((item) => (
                    <li key={item.node_type}>
                      <button
                        type="button"
                        disabled={insertEdge === null}
                        onClick={() => addStep(item)}
                        className={cn(
                          "w-full rounded-control border border-transparent px-2.5 py-1.5 text-left transition-colors",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                          insertEdge === null ? "cursor-default opacity-70" : "hover:border-border hover:bg-muted",
                        )}
                      >
                        <span className="flex items-center gap-1.5 text-[13px] font-medium text-foreground">
                          {item.name}
                          {item.needs_approval ? <ShieldCheck size={13} className="text-warning" aria-label="Needs an approval before it" /> : null}
                        </span>
                        <span className="block text-[12px] leading-4 text-text-secondary">{item.description}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </aside>

        {/* Center: the graph */}
        <section className="flex min-h-0 flex-col overflow-auto bg-background p-4" aria-label="Workflow graph">
          <SectionLabel>{detail.name}</SectionLabel>
          <div className="mt-4 flex-1 overflow-x-auto pb-4">
            <WorkflowGraph
              graph={graph}
              selectedId={selected}
              onSelect={(id) => {
                setSelected(id);
                setInsertEdge(null);
              }}
              onInsert={(index) => setInsertEdge((current) => (current === index ? null : index))}
              insertEdge={insertEdge}
              decorate={(node) => {
                const original = detail.workflow.nodes.find((n) => n.id === node.id);
                const current = draft.nodes.find((n) => n.id === node.id);
                if (!original) return { tone: "new", tag: "New", sub: node.type_title };
                if (JSON.stringify(original.data) !== JSON.stringify(current?.data)) {
                  return { tone: "changed", tag: "Changed", sub: node.type_title };
                }
                return { sub: node.type_title };
              }}
            />
          </div>
          <p className="text-[12.5px] text-text-secondary">
            Changes stay in this editor until you review them. Nothing goes live until you publish.
          </p>
        </section>

        {/* Right: step settings */}
        <aside className="flex min-h-0 flex-col border-t border-border bg-surface lg:border-l lg:border-t-0" aria-label="Step settings">
          {selectedNode ? (
            <>
              <div className="flex-1 space-y-4 overflow-y-auto p-4">
                <div>
                  <SectionLabel>Step settings</SectionLabel>
                  <h3 className="mt-2 text-[16px] font-semibold text-foreground">{nodeLabel(selectedNode)}</h3>
                  <p className="font-mono text-[12px] text-text-secondary">{selectedNode.data.nodeType}</p>
                </div>
                <StepSettings
                  node={selectedNode}
                  item={libraryByType.get(selectedNode.data.nodeType)}
                  onChange={(data) => setDraft(updateNodeData(draft, selectedNode.id, data))}
                />
              </div>
              {!FIXED_NODE_TYPES.has(selectedNode.data.nodeType) ? (
                <div className="border-t border-border p-3">
                  <Button
                    variant="secondary"
                    className="w-full text-danger"
                    onClick={() => {
                      setDraft(removeNode(draft, selectedNode.id));
                      setSelected(null);
                    }}
                  >
                    <Trash2 size={14} className="mr-1.5" aria-hidden /> Remove this step
                  </Button>
                </div>
              ) : null}
            </>
          ) : (
            <p className="p-4 text-[13px] text-text-secondary">Select a step to change its settings.</p>
          )}
          {error ? <p role="alert" className="px-4 pb-3 text-[12.5px] text-danger">{error}</p> : null}
        </aside>
      </div>
    </div>
  );
}
