"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, WandSparkles } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

import { studioApi, type StudioWorkflow, type WorkflowDraft } from "./api";

const NEW_WORKFLOW = "new";

/** Type a request: TCOS drafts a change to a workflow, or a brand-new workflow. */
export function AskBar({ workflows, onDraft }: { workflows: StudioWorkflow[]; onDraft: (draft: WorkflowDraft) => void }) {
  const router = useRouter();
  const [workflowId, setWorkflowId] = useState(workflows[0]?.id ?? NEW_WORKFLOW);
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!workflowId || request.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      if (workflowId === NEW_WORKFLOW) {
        onDraft(await studioApi.draftWorkflow(request.trim()));
        setRequest("");
        setBusy(false);
        return;
      }
      const proposal = await studioApi.createProposal(workflowId, request.trim());
      router.push(`/app/workflows/proposals/${proposal.id}`);
    } catch (err) {
      setError(apiErrorMessage(err, "TCOS could not draft this change."));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-container border border-ai-accent/50 bg-surface p-3">
      <p className="mb-2 flex flex-wrap items-center gap-x-2 text-[14px] font-semibold text-foreground">
        <span className="flex items-center gap-1.5 text-ai-accent"><WandSparkles size={16} aria-hidden /> Ask TCOS</span>
        <span className="text-[13px] font-normal text-text-secondary">Type what you want. TCOS changes a workflow or builds a new one for you to review.</span>
      </p>
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <label className="sr-only" htmlFor="ask-workflow">Workflow to change</label>
        <select
          id="ask-workflow"
          value={workflowId}
          onChange={(e) => setWorkflowId(e.target.value)}
          className="h-10 shrink-0 rounded-control border border-border bg-surface px-2 text-[13px] text-foreground md:max-w-56"
        >
          {workflows.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
          <option value={NEW_WORKFLOW}>+ New workflow</option>
        </select>
        <label className="sr-only" htmlFor="ask-request">Describe the change</label>
        <input
          id="ask-request"
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder={workflowId === NEW_WORKFLOW
            ? "Describe the new workflow, e.g. answer questions about gift wrapping from the help articles"
            : "Describe a change, e.g. if a delivery is more than 2 days late, apologise and offer a person"}
          className="h-10 min-w-0 shrink-0 rounded-control border border-border bg-background md:flex-1 md:shrink px-3 text-[14px] text-foreground placeholder:text-text-secondary focus-visible:border-ai-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ai-accent/30"
        />
        <Button type="submit" size="md" disabled={busy || !workflowId || request.trim().length < 3} className="h-10">
          {busy ? <Loader2 size={15} className="mr-1.5 animate-spin" aria-hidden /> : null}
          {busy ? "Drafting…" : "Draft it"}
        </Button>
      </div>
      {error ? <p role="alert" className="px-2 pb-1 pt-2 text-[12.5px] text-danger">{error}</p> : null}
    </form>
  );
}
