"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUp, Check, Equal, Loader2, Plus, TriangleAlert, Waves } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { cn } from "@/platform/utils";
import { Button } from "@/ui/primitives/button";
import { ConfirmDialog } from "@/ui/overlay/ConfirmDialog";

import { ToneChip } from "../inbox/case/parts";
import { ProposalTestPanel, testsAllowPublish } from "./ProposalTestPanel";
import { WorkflowGraph, type NodeDecoration } from "./WorkflowGraph";
import { studioApi, type Graph, type GraphNode, type Proposal, type SummaryLine } from "./api";

const summaryIcon: Record<SummaryLine["kind"], { icon: typeof Plus; className: string; label: string }> = {
  new: { icon: Plus, className: "bg-warning/10 text-warning", label: "New" },
  changed: { icon: Waves, className: "bg-primary/10 text-primary", label: "Changed" },
  same: { icon: Equal, className: "bg-muted text-text-secondary", label: "Unchanged" },
};

// Proposed graph plus the steps it removes, so removals stay visible in place.
function mergedGraph(proposal: Proposal): Graph {
  const removed = new Set(proposal.diff.removed);
  if (!removed.size) return proposal.graph;
  return {
    nodes: [...proposal.graph.nodes, ...proposal.base_graph.nodes.filter((n) => removed.has(n.id))],
    edges: [
      ...proposal.graph.edges,
      ...proposal.base_graph.edges.filter((e) => removed.has(e.source) || removed.has(e.target)),
    ],
  };
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[11.5px] font-semibold uppercase tracking-wide text-text-secondary">{children}</h2>;
}

export default function ProposalScreen({ proposalId }: { proposalId: string }) {
  const router = useRouter();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refineText, setRefineText] = useState("");
  const [busy, setBusy] = useState<"refine" | "test" | "publish" | "discard" | null>(null);
  const [confirmPublish, setConfirmPublish] = useState(false);

  useEffect(() => {
    studioApi.proposal(proposalId).then(setProposal).catch((err) => setError(apiErrorMessage(err, "Could not load this proposal.")));
  }, [proposalId]);

  const decorate = useMemo(() => {
    if (!proposal) return undefined;
    const isNew = new Set(proposal.diff.new);
    const changed = new Set(proposal.diff.changed);
    const removed = new Set(proposal.diff.removed);
    return (node: GraphNode): NodeDecoration => {
      if (isNew.has(node.id)) return { tone: "new", tag: "New", sub: node.type_title };
      if (changed.has(node.id)) return { tone: "changed", tag: "Changed", sub: node.type_title };
      if (removed.has(node.id)) return { tone: "removed", tag: "Removed", sub: node.type_title };
      return { sub: node.type_title };
    };
  }, [proposal]);

  if (error && !proposal) {
    return <p role="alert" className="p-6 text-[13.5px] text-danger">{error}</p>;
  }
  if (!proposal) {
    return (
      <p className="flex items-center gap-2 p-6 text-[13.5px] text-text-secondary">
        <Loader2 size={15} className="animate-spin" aria-hidden /> Loading proposal…
      </p>
    );
  }

  const isDraft = proposal.status === "draft";
  const blocked = proposal.validation_errors.length > 0;
  const canPublish = !blocked && testsAllowPublish(proposal.test_results);
  const touched = new Set([...proposal.diff.new, ...proposal.diff.changed]);

  const refine = async (event: React.FormEvent) => {
    event.preventDefault();
    if (refineText.trim().length < 3) return;
    setBusy("refine");
    setError(null);
    try {
      setProposal(await studioApi.refineProposal(proposal.id, refineText.trim()));
      setRefineText("");
    } catch (err) {
      setError(apiErrorMessage(err, "TCOS could not update this change."));
    } finally {
      setBusy(null);
    }
  };

  const runTest = async () => {
    setBusy("test");
    setError(null);
    try {
      const results = await studioApi.testProposal(proposal.id);
      setProposal({ ...proposal, test_results: results });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not test this change."));
    } finally {
      setBusy(null);
    }
  };

  const publish = async () => {
    setBusy("publish");
    setError(null);
    try {
      await studioApi.publishProposal(proposal.id);
      router.push("/app/workflows");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not publish. Check the problems listed on the right."));
      setBusy(null);
      setConfirmPublish(false);
    }
  };

  const discard = async () => {
    setBusy("discard");
    try {
      await studioApi.discardProposal(proposal.id);
      router.push("/app/workflows");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not discard this proposal."));
      setBusy(null);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface px-4 py-2.5">
        <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-[13.5px]">
          <Link href="/app/workflows" className="text-text-secondary hover:text-foreground">Workflows</Link>
          <span className="text-text-secondary">/</span>
          <span className="truncate text-text-secondary">{proposal.workflow_name}</span>
          <span className="text-text-secondary">/</span>
          <span className="font-semibold text-foreground">v{proposal.version} {isDraft ? "draft" : proposal.status}</span>
          {isDraft ? <ToneChip tone="attention" className="ml-1">Proposed change · not live</ToneChip> : null}
        </nav>
        <div className="flex items-center gap-3">
          <span className="hidden font-mono text-[12px] tabular-nums text-text-secondary md:inline">
            {proposal.diff.new.length} new · {proposal.diff.changed.length} changed
            {proposal.diff.removed.length ? ` · ${proposal.diff.removed.length} removed` : ""}
            {proposal.live_version ? ` · live is v${proposal.live_version}` : ""}
          </span>
          {isDraft ? (
            <>
              <Button variant="secondary" size="sm" disabled={busy !== null} onClick={() => void discard()}>Discard</Button>
              <Button size="sm" disabled={busy !== null || !canPublish} onClick={() => setConfirmPublish(true)}>
                Publish v{proposal.version}
              </Button>
            </>
          ) : null}
        </div>
      </div>

      <div className="grid min-h-0 flex-1 auto-rows-max grid-cols-1 overflow-y-auto lg:auto-rows-auto lg:grid-cols-[300px_minmax(0,1fr)_340px] lg:overflow-hidden">
        {/* Left: what was asked, what changes, refine */}
        <aside className="flex min-h-0 flex-col border-b border-border bg-surface lg:border-b-0 lg:border-r">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <SectionLabel>Ask TCOS</SectionLabel>
            <ul className="space-y-2">
              {proposal.requests.map((request, index) => (
                <li key={index} className="rounded-container bg-primary/[0.07] px-3 py-2 text-[13.5px] leading-5 text-foreground">
                  {request}
                </li>
              ))}
            </ul>
            <div className="rounded-container border border-border p-3">
              <h3 className="text-[13.5px] font-semibold text-foreground">Here&apos;s the change I&apos;d make:</h3>
              {proposal.summary.length ? (
                <ul className="mt-2 space-y-2">
                  {proposal.summary.map((line, index) => {
                    const { icon: Icon, className, label } = summaryIcon[line.kind];
                    return (
                      <li key={index} className="flex gap-2 text-[13px] leading-5 text-foreground">
                        <span className={cn("mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded", className)} title={label}>
                          <Icon size={12} aria-hidden />
                          <span className="sr-only">{label}:</span>
                        </span>
                        <span className={line.kind === "same" ? "text-text-secondary" : undefined}>{line.text}</span>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-2 text-[13px] text-text-secondary">No summary was returned. Check the highlighted steps.</p>
              )}
            </div>
          </div>
          {isDraft ? (
            <form onSubmit={refine} className="border-t border-border p-3">
              <label htmlFor="refine" className="sr-only">Ask for another change</label>
              <div className="flex items-center gap-2 rounded-container border border-border px-2 py-1.5 focus-within:ring-2 focus-within:ring-focus">
                <input
                  id="refine"
                  value={refineText}
                  onChange={(e) => setRefineText(e.target.value)}
                  placeholder="Ask for another change"
                  disabled={busy !== null}
                  className="min-w-0 flex-1 bg-transparent text-[13.5px] text-foreground placeholder:text-text-secondary focus:outline-none"
                />
                <Button type="submit" size="sm" className="h-8 w-8 px-0" disabled={busy !== null || refineText.trim().length < 3} aria-label="Send">
                  {busy === "refine" ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <ArrowUp size={14} aria-hidden />}
                </Button>
              </div>
            </form>
          ) : null}
        </aside>

        {/* Center: graph with the change marked in place */}
        <section className="min-h-0 overflow-auto bg-background p-4" aria-label="Workflow graph">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <SectionLabel>{proposal.workflow_name} · v{proposal.version} {isDraft ? "draft" : ""}</SectionLabel>
            <ul className="flex gap-3 text-[12px] text-text-secondary" aria-label="Legend">
              <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-dashed border-warning" />New</li>
              <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-primary" />Changed</li>
              <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-border" />Same as v{proposal.base_version}</li>
            </ul>
          </div>
          <div className="overflow-x-auto pb-4">
            <WorkflowGraph
              graph={mergedGraph(proposal)}
              decorate={decorate}
              highlightEdge={(source, target) => touched.has(source) || touched.has(target)}
            />
          </div>
        </section>

        {/* Right: checks and real past conversations */}
        <aside className="flex min-h-0 flex-col border-t border-border bg-surface lg:border-l lg:border-t-0">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <SectionLabel>Before you publish</SectionLabel>
            {blocked ? (
              <div role="alert" className="rounded-container border border-danger/30 bg-danger/5 p-3">
                <p className="flex items-center gap-1.5 text-[13.5px] font-semibold text-danger">
                  <TriangleAlert size={15} aria-hidden /> Fix {proposal.validation_errors.length === 1 ? "this" : "these"} first
                </p>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-[13px] text-foreground">
                  {proposal.validation_errors.map((message) => <li key={message}>{message}</li>)}
                </ul>
              </div>
            ) : (
              <div className="rounded-container border border-commerce-accent/30 bg-commerce-accent/5 p-3">
                <p className="flex items-center gap-1.5 text-[13.5px] font-semibold text-commerce-accent">
                  <Check size={15} aria-hidden /> Checks passed
                </p>
                <p className="mt-1 text-[12.5px] text-text-secondary">
                  The workflow is complete, every step type is available, and order changes have an approval before them.
                </p>
              </div>
            )}
            <ProposalTestPanel proposal={proposal} testing={busy === "test"} onTest={() => void runTest()} />
            {error ? <p role="alert" className="text-[12.5px] text-danger">{error}</p> : null}
          </div>
          {isDraft ? (
            <div className="flex gap-2 border-t border-border p-3">
              <Button className="flex-1" disabled={busy !== null || !canPublish} onClick={() => setConfirmPublish(true)}>
                Publish as v{proposal.version}
              </Button>
              <Button variant="secondary" disabled={busy !== null} onClick={() => router.push("/app/workflows")}>
                Keep draft
              </Button>
            </div>
          ) : null}
        </aside>
      </div>

      <ConfirmDialog
        open={confirmPublish}
        onOpenChange={setConfirmPublish}
        title={`Publish v${proposal.version}?`}
        description={
          <p>
            New customer messages for {proposal.workflow_name} will use this version right away. v{proposal.base_version} stays in version history.
          </p>
        }
        confirmLabel={`Publish v${proposal.version}`}
        busy={busy === "publish"}
        onConfirm={() => void publish()}
      />
    </div>
  );
}
