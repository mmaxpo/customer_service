"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

import { formatShortAgo } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { MiniGraph } from "./WorkflowGraph";
import { studioApi, type StudioWorkflow } from "./api";

function statusChip(workflow: StudioWorkflow) {
  if (!workflow.enabled) return <ToneChip tone="neutral">Off</ToneChip>;
  return (
    <ToneChip tone="commerce">
      Live{workflow.live_version ? ` · v${workflow.live_version}` : ""}
    </ToneChip>
  );
}

export function WorkflowCard({ workflow, onChanged }: { workflow: StudioWorkflow; onChanged: () => void }) {
  const [switching, setSwitching] = useState(false);
  const [keywords, setKeywords] = useState<string | null>(null); // null = not editing
  const [error, setError] = useState<string | null>(null);
  const run = (action: Promise<unknown>, fallback: string) => {
    setSwitching(true);
    setError(null);
    action.then(onChanged).catch((err) => setError(apiErrorMessage(err, fallback))).finally(() => setSwitching(false));
  };
  const toggle = () => run(studioApi.setWorkflowEnabled(workflow.id, !workflow.enabled), "Could not change this workflow.");
  const saveKeywords = (event: React.FormEvent) => {
    event.preventDefault();
    const list = (keywords ?? "").split(",").map((word) => word.trim()).filter(Boolean);
    if (!list.length) return;
    run(studioApi.setWorkflowKeywords(workflow.id, list).then(() => setKeywords(null)), "Could not save the keywords.");
  };
  const remove = () => {
    if (window.confirm(`Delete "${workflow.name}"? This can't be undone.`)) {
      run(studioApi.deleteWorkflow(workflow.id), "Could not delete this workflow.");
    }
  };
  const answeredRate = workflow.runs_7d ? Math.round((workflow.answered_7d / workflow.runs_7d) * 100) : null;

  return (
    <li className="flex flex-col rounded-container border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-foreground">{workflow.name}</h2>
        {statusChip(workflow)}
      </div>
      <p className="mt-1.5 text-[13px] leading-5 text-text-secondary">
        {workflow.description || "No description yet."}
        {workflow.dispatch_mode === "fallback" ? " Runs when no other workflow matches." : null}
      </p>
      {keywords !== null ? (
        <form onSubmit={saveKeywords} className="mt-2 flex flex-wrap items-center gap-2">
          <label htmlFor={`keywords-${workflow.id}`} className="sr-only">Keywords, separated by commas</label>
          <input
            id={`keywords-${workflow.id}`}
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="gift wrap, gift note"
            className="h-8 min-w-0 flex-1 rounded-control border border-border bg-surface px-2 text-[13px] text-foreground"
          />
          <Button type="submit" size="sm" disabled={switching || !keywords.trim()}>Save</Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setKeywords(null)}>Cancel</Button>
        </form>
      ) : workflow.keywords.length ? (
        <p className="mt-1.5 text-[12.5px] leading-5 text-text-secondary">
          Runs when a message contains: <span className="text-foreground">{workflow.keywords.join(", ")}</span>
          {workflow.can_toggle ? (
            <button type="button" onClick={() => setKeywords(workflow.keywords.join(", "))} className="ml-2 font-medium text-primary hover:underline">
              Edit keywords
            </button>
          ) : null}
        </p>
      ) : null}
      {error ? <p role="alert" className="mt-1.5 text-[12.5px] text-danger">{error}</p> : null}
      <div className="mb-4 mt-3">
        <MiniGraph graph={workflow.graph} />
      </div>

      {workflow.open_proposal_id ? (
        <Link
          href={`/app/workflows/proposals/${workflow.open_proposal_id}`}
          className="-mt-1 mb-4 inline-flex items-center gap-1 self-start text-[13px] font-medium text-warning hover:underline"
        >
          A change is waiting for review <ArrowRight size={14} aria-hidden />
        </Link>
      ) : null}

      <div className="mt-auto border-t border-border pt-3 text-[12.5px] tabular-nums text-text-secondary">
        <p>
          {workflow.runs_7d} {workflow.runs_7d === 1 ? "chat" : "chats"} in 7 days
          {answeredRate !== null ? (
            <span className={answeredRate > 0 ? "text-commerce-accent" : undefined}> · {answeredRate}% answered</span>
          ) : null}
          <span> · edited {formatShortAgo(workflow.edited_at)}</span>
        </p>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-medium">
          <Link href={`/app/workflows/edit/${workflow.id}`} className="text-primary hover:underline">Edit steps</Link>
          <Link href={`/app/workflows/history/${workflow.id}`} className="text-primary hover:underline">Version history</Link>
          {workflow.can_toggle ? (
            <button type="button" onClick={toggle} disabled={switching} className="ml-auto text-primary hover:underline disabled:opacity-60">
              {workflow.enabled ? "Turn off" : "Turn on"}
            </button>
          ) : null}
          {workflow.can_toggle && !workflow.enabled ? (
            <button type="button" onClick={remove} disabled={switching} className="text-danger hover:underline disabled:opacity-60">Delete</button>
          ) : null}
        </div>
      </div>
    </li>
  );
}
