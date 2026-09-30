"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleAlert, Flag, Loader2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { cn } from "@/platform/utils";
import { Button } from "@/ui/primitives/button";

import { formatDay, formatTime, humanize } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { WorkflowGraph, type NodeDecoration } from "./WorkflowGraph";
import { studioApi, type GraphNode, type RunDetail, type RunStep } from "./api";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[11.5px] font-semibold uppercase tracking-wide text-text-secondary">{children}</h2>;
}

function formatDuration(ms?: number) {
  if (ms === undefined) return null;
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

// One plain sentence tracing the problem to a step, from what the run recorded.
function causeNote(run: RunDetail, label: (id: string) => string): string | null {
  const step = run.steps.find((s) => s.node_id === run.likely_cause);
  if (step?.problem === "error") return `${label(step.node_id)} failed: ${step.error ?? "no error message was recorded"}.`;
  if (step?.problem === "handoff_required") {
    return step.meta?.provider_failure_code
      ? `${label(step.node_id)} couldn't get an answer from the AI provider, so the customer got a fallback reply and the chat was handed to your team.`
      : `${label(step.node_id)} asked for a person to take over.`;
  }
  if (run.status === "failed") return `The run stopped before finishing: ${run.failure ?? "no error was recorded"}.`;
  return null;
}

function stepDecoration(step: RunStep | undefined, isCause: boolean, node: GraphNode): NodeDecoration {
  const duration = formatDuration(step?.duration_ms);
  if (isCause) return { tone: "cause", tag: "Likely cause", sub: duration ?? node.type_title };
  if (!step) return { tone: "skipped", tag: "Not run", sub: node.type_title };
  if (step.status === "error") return { tone: "error", tag: "Error", sub: node.type_title };
  if (step.status === "skipped") return { tone: "skipped", tag: "Skipped", sub: node.type_title };
  return { sub: duration ? `${node.type_title} · ${duration}` : node.type_title };
}

export default function RunReviewScreen({ runId }: { runId: string }) {
  const router = useRouter();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [fix, setFix] = useState("");
  const [flagFor, setFlagFor] = useState<string | null>(null);
  const [flagNote, setFlagNote] = useState("");
  const [busy, setBusy] = useState<"fix" | "dismiss" | "flag" | null>(null);

  const load = () =>
    studioApi
      .run(runId)
      .then((data) => {
        setRun(data);
        setSelected((current) => current ?? data.likely_cause ?? data.graph.nodes[0]?.id ?? null);
      })
      .catch((err) => setError(apiErrorMessage(err, "Could not load this run.")));

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const stepsById = useMemo(() => new Map((run?.steps ?? []).map((s) => [s.node_id, s])), [run]);
  const labelOf = (id: string) => run?.graph.nodes.find((n) => n.id === id)?.label ?? humanize(id);

  if (error && !run) return <p role="alert" className="p-6 text-[13.5px] text-danger">{error}</p>;
  if (!run) {
    return (
      <p className="flex items-center gap-2 p-6 text-[13.5px] text-text-secondary">
        <Loader2 size={15} className="animate-spin" aria-hidden /> Loading run…
      </p>
    );
  }

  const selectedNode = run.graph.nodes.find((n) => n.id === selected) ?? null;
  const selectedStep = selected ? stepsById.get(selected) : undefined;
  const note = causeNote(run, labelOf);
  const flaggedMessages = new Set(run.flags.map((f) => f.message_id).filter(Boolean));
  const ranSteps = run.steps.filter((s) => s.status === "done" || s.status === "error").length;

  const proposeFix = async () => {
    if (!run.workflow_id || !selectedNode || fix.trim().length < 3) return;
    setBusy("fix");
    setError(null);
    try {
      const proposal = await studioApi.createProposal(run.workflow_id, `In the "${selectedNode.label}" step: ${fix.trim()}`);
      router.push(`/app/workflows/proposals/${proposal.id}`);
    } catch (err) {
      setError(apiErrorMessage(err, "TCOS could not draft this fix."));
      setBusy(null);
    }
  };

  const dismiss = async () => {
    setBusy("dismiss");
    try {
      await studioApi.dismissRun(run.run_id);
      router.push("/app/workflows/review");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not clear this review."));
      setBusy(null);
    }
  };

  const submitFlag = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!flagFor || !flagNote.trim()) return;
    setBusy("flag");
    try {
      await studioApi.flagRun(run.run_id, { note: flagNote.trim(), message_id: flagFor, step_id: selected });
      setFlagFor(null);
      setFlagNote("");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save the flag."));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface px-4 py-2.5">
        <nav aria-label="Breadcrumb" className="flex min-w-0 flex-wrap items-center gap-1.5 text-[13.5px]">
          <Link href="/app/workflows/review" className="text-text-secondary hover:text-foreground">Needs review</Link>
          <span className="text-text-secondary">/</span>
          <span className="truncate font-semibold text-foreground">
            {run.workflow_name ?? "Workflow run"}{run.version ? ` · v${run.version}` : ""}
          </span>
          {run.review_reasons.length ? <ToneChip tone="attention" className="ml-1">Needs review</ToneChip> : null}
        </nav>
        <div className="flex items-center gap-3">
          <span className="hidden font-mono text-[12px] tabular-nums text-text-secondary md:inline">
            {formatDay(run.created_at)} {formatTime(run.created_at)} · {ranSteps} steps
            {run.elapsed_sec ? ` · ${run.elapsed_sec.toFixed(1)}s` : ""}
          </span>
          {run.conversation_id ? (
            <Link
              href={`/app/inbox?conversation=${run.conversation_id}`}
              className="inline-flex h-8 items-center rounded-control border border-border bg-surface px-3 text-xs font-semibold text-foreground hover:bg-muted"
            >
              Open conversation
            </Link>
          ) : null}
        </div>
      </div>

      <div className="grid min-h-0 flex-1 auto-rows-max grid-cols-1 overflow-y-auto lg:auto-rows-auto lg:grid-cols-[300px_minmax(0,1fr)_340px] lg:overflow-hidden">
        {/* Left: the conversation */}
        <aside className="min-h-0 overflow-y-auto border-b border-border bg-surface p-4 lg:border-b-0 lg:border-r">
          <SectionLabel>Conversation</SectionLabel>
          {run.transcript.length ? (
            <ul className="mt-3 space-y-3">
              {run.transcript.map((message) => {
                const fromCustomer = message.sender === "customer";
                const flagged = flaggedMessages.has(message.id);
                return (
                  <li key={message.id}>
                    <p
                      className={cn(
                        "rounded-container px-3 py-2 text-[13.5px] leading-5",
                        fromCustomer ? "mr-6 bg-muted text-foreground" : "ml-6 border border-border bg-surface text-foreground",
                        flagged && "border-warning ring-1 ring-warning",
                      )}
                    >
                      {message.body}
                    </p>
                    <div className={cn("mt-1 flex items-center gap-2 text-[11.5px] text-text-secondary", !fromCustomer && "ml-6")}>
                      <span>{fromCustomer ? "Customer" : humanize(message.sender)} · {formatTime(message.created_at)}</span>
                      {flagged ? (
                        <span className="flex items-center gap-1 font-medium text-warning"><Flag size={11} aria-hidden /> Marked as wrong</span>
                      ) : !fromCustomer ? (
                        <button type="button" onClick={() => setFlagFor(message.id)} className="font-medium text-primary hover:underline">
                          Mark as wrong
                        </button>
                      ) : null}
                    </div>
                    {flagFor === message.id ? (
                      <form onSubmit={submitFlag} className="ml-6 mt-2 space-y-2">
                        <label htmlFor={`flag-${message.id}`} className="sr-only">What was wrong?</label>
                        <textarea
                          id={`flag-${message.id}`}
                          value={flagNote}
                          onChange={(e) => setFlagNote(e.target.value)}
                          rows={2}
                          placeholder="What was wrong with this answer?"
                          className="w-full rounded-control border border-border px-2 py-1.5 text-[13px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                        />
                        <div className="flex gap-2">
                          <Button type="submit" size="sm" disabled={busy !== null || !flagNote.trim()}>Save flag</Button>
                          <Button variant="ghost" size="sm" onClick={() => setFlagFor(null)}>Cancel</Button>
                        </div>
                      </form>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mt-3 text-[13px] text-text-secondary">No conversation is linked to this run.</p>
          )}
        </aside>

        {/* Center: what happened */}
        <section className="flex min-h-0 flex-col overflow-auto bg-background p-4" aria-label="What happened in this conversation">
          <SectionLabel>What happened in this conversation</SectionLabel>
          <div className="mt-4 shrink-0 overflow-x-auto pb-4 lg:flex-1">
            <WorkflowGraph
              graph={run.graph}
              selectedId={selected}
              onSelect={setSelected}
              decorate={(node) => stepDecoration(stepsById.get(node.id), node.id === run.likely_cause, node)}
            />
          </div>
          {note ? (
            <p className="mt-2 flex gap-2 rounded-container border border-border bg-surface px-3 py-2.5 text-[13px] leading-5 text-foreground">
              <CircleAlert size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
              {note}
            </p>
          ) : null}
        </section>

        {/* Right: selected step */}
        <aside className="flex min-h-0 flex-col border-t border-border bg-surface lg:border-l lg:border-t-0">
          {selectedNode ? (
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              <div>
                <SectionLabel>Selected step</SectionLabel>
                <h3 className="mt-2 text-[16px] font-semibold text-foreground">{selectedNode.label}</h3>
                <p className="text-[12.5px] text-text-secondary">
                  {selectedNode.type_title}
                  {formatDuration(selectedStep?.duration_ms) ? ` · ${formatDuration(selectedStep?.duration_ms)}` : ""}
                  {selectedStep ? ` · ${humanize(selectedStep.status)}` : " · not run"}
                </p>
              </div>

              {selectedStep?.status === "skipped" ? (
                <p className="text-[13px] text-text-secondary">Skipped because the route before it went another way.</p>
              ) : null}

              {selectedStep?.error ? (
                <div>
                  <SectionLabel>Error</SectionLabel>
                  <p className="mt-1.5 text-[13px] text-danger">{selectedStep.error}</p>
                </div>
              ) : null}

              {selectedStep?.output ? (
                <div>
                  <SectionLabel>What it produced</SectionLabel>
                  <pre className="mt-1.5 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-control bg-muted p-2.5 font-mono text-[11.5px] leading-5 text-foreground">
                    {selectedStep.output}
                  </pre>
                </div>
              ) : null}

              {selectedStep?.meta && Object.keys(selectedStep.meta).length ? (
                <div>
                  <SectionLabel>Details</SectionLabel>
                  <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono text-[11.5px]">
                    {Object.entries(selectedStep.meta).map(([key, value]) => (
                      <div key={key} className="contents">
                        <dt className="text-text-secondary">{key}</dt>
                        <dd className="break-all text-foreground">{typeof value === "string" ? value : JSON.stringify(value)}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ) : null}

              <div>
                <label htmlFor="fix" className="text-[11.5px] font-semibold uppercase tracking-wide text-warning">Fix this step</label>
                <textarea
                  id="fix"
                  value={fix}
                  onChange={(e) => setFix(e.target.value)}
                  rows={4}
                  placeholder={`Describe how "${selectedNode.label}" should behave instead`}
                  className="mt-1.5 w-full rounded-control border border-border px-2.5 py-2 text-[13px] leading-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                />
                <p className="mt-1 text-[12px] text-text-secondary">
                  {run.workflow_id
                    ? `This becomes a proposed change to ${run.workflow_name}. You'll review it before it goes live.`
                    : "This run isn't linked to a saved workflow, so a fix can't be proposed from here."}
                </p>
              </div>
              {error ? <p role="alert" className="text-[12.5px] text-danger">{error}</p> : null}
            </div>
          ) : (
            <p className="flex-1 p-4 text-[13px] text-text-secondary">Select a step to see what it did.</p>
          )}
          <div className="flex gap-2 border-t border-border p-3">
            <Button
              className="flex-1"
              disabled={busy !== null || !run.workflow_id || !selectedNode || fix.trim().length < 3}
              onClick={() => void proposeFix()}
            >
              {busy === "fix" ? "Drafting…" : "Propose fix"}
            </Button>
            <Button variant="secondary" disabled={busy !== null} onClick={() => void dismiss()}>
              Not a problem
            </Button>
          </div>
        </aside>
      </div>
    </div>
  );
}
