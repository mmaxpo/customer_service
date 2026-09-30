"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ChevronRight, Loader2, WandSparkles } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

import { formatShortAgo } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { AutomationHeader } from "./AutomationHeader";
import { MiniGraph } from "./WorkflowGraph";
import { studioApi, type StudioOverview, type StudioWorkflow } from "./api";

function statusChip(workflow: StudioWorkflow) {
  if (!workflow.enabled) return <ToneChip tone="neutral">Off</ToneChip>;
  return (
    <ToneChip tone="commerce">
      Live{workflow.live_version ? ` · v${workflow.live_version}` : ""}
    </ToneChip>
  );
}

function WorkflowCard({ workflow }: { workflow: StudioWorkflow }) {
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

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-border pt-3 text-[12.5px] tabular-nums text-text-secondary">
        <span>
          {workflow.runs_7d} {workflow.runs_7d === 1 ? "chat" : "chats"}
          {answeredRate !== null ? (
            <span className={answeredRate > 0 ? "ml-2 text-commerce-accent" : "ml-2"}>{answeredRate}% answered</span>
          ) : null}
        </span>
        <span className="flex items-center gap-3">
          <span>edited {formatShortAgo(workflow.edited_at)}</span>
          <Link href={`/app/workflows/edit/${workflow.id}`} className="font-sans font-medium text-primary hover:underline">
            Edit steps
          </Link>
        </span>
      </div>
    </li>
  );
}

function AskBar({ workflows }: { workflows: StudioWorkflow[] }) {
  const router = useRouter();
  const [workflowId, setWorkflowId] = useState(workflows[0]?.id ?? "");
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!workflowId || request.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      const proposal = await studioApi.createProposal(workflowId, request.trim());
      router.push(`/app/workflows/proposals/${proposal.id}`);
    } catch (err) {
      setError(apiErrorMessage(err, "TCOS could not draft this change."));
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-container border border-border bg-surface p-2">
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <span className="flex shrink-0 items-center gap-1.5 px-2 text-[13.5px] font-semibold text-ai-accent">
          <WandSparkles size={16} aria-hidden /> Ask TCOS
        </span>
        <label className="sr-only" htmlFor="ask-workflow">Workflow to change</label>
        <select
          id="ask-workflow"
          value={workflowId}
          onChange={(e) => setWorkflowId(e.target.value)}
          className="h-9 shrink-0 rounded-control border border-border bg-surface px-2 text-[13px] text-foreground md:max-w-56"
        >
          {workflows.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
        <label className="sr-only" htmlFor="ask-request">Describe the change</label>
        <input
          id="ask-request"
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="Describe a change, e.g. if a delivery is more than 2 days late, apologise and offer a person"
          className="h-9 min-w-0 flex-1 rounded-control px-2 text-[13.5px] text-foreground placeholder:text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        />
        <Button type="submit" size="md" disabled={busy || !workflowId || request.trim().length < 3} className="h-9">
          {busy ? <Loader2 size={15} className="mr-1.5 animate-spin" aria-hidden /> : null}
          {busy ? "Drafting…" : "Draft it"}
        </Button>
      </div>
      {error ? <p role="alert" className="px-2 pb-1 pt-2 text-[12.5px] text-danger">{error}</p> : null}
    </form>
  );
}

export default function WorkflowsScreen() {
  const [data, setData] = useState<StudioOverview | null>(null);
  const [reviewCount, setReviewCount] = useState<number>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    studioApi.overview().then(setData).catch((err) => setError(apiErrorMessage(err, "Could not load workflows.")));
    studioApi.reviewQueue().then((runs) => setReviewCount(runs.length)).catch(() => {});
  }, []);

  const live = data?.workflows.filter((w) => w.enabled).length ?? 0;

  return (
    <div className="mx-auto max-w-6xl">
      <AutomationHeader
        title="Workflows"
        description="Every customer message goes to the workflow that fits. Anything that doesn't fit goes to your team."
        reviewCount={reviewCount}
        actions={
          <Link
            href="/app/workflows/templates"
            className="text-[13px] font-medium text-text-secondary hover:text-foreground hover:underline"
          >
            Templates & builder
          </Link>
        }
      />

      {error ? <p role="alert" className="text-[13.5px] text-danger">{error}</p> : null}
      {!data && !error ? (
        <p className="flex items-center gap-2 text-[13.5px] text-text-secondary">
          <Loader2 size={15} className="animate-spin" aria-hidden /> Loading workflows…
        </p>
      ) : null}

      {data ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-container border border-border bg-surface px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
            <ol className="flex flex-wrap items-center gap-2 text-[13px]" aria-label="How messages are routed">
              <li className="rounded-control bg-muted px-2.5 py-1 text-foreground">Customer message</li>
              <ChevronRight size={14} className="text-text-secondary" aria-hidden />
              <li className="rounded-control bg-muted px-2.5 py-1 text-foreground">Matched to a workflow</li>
              <ChevronRight size={14} className="text-text-secondary" aria-hidden />
              <li className="rounded-control bg-commerce-accent/10 px-2.5 py-1 font-medium text-commerce-accent">
                {live} live {live === 1 ? "workflow" : "workflows"}
              </li>
              <li className="px-1 text-text-secondary">or</li>
              <li className="rounded-control bg-muted px-2.5 py-1 text-foreground">No match → your team</li>
            </ol>
            <p className="font-mono text-[12px] tabular-nums text-text-secondary">
              last 7 days · {data.routing.messages_7d} customer messages
            </p>
          </div>

          {data.workflows.length ? <AskBar workflows={data.workflows} /> : null}

          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.workflows.map((workflow) => (
              <WorkflowCard key={workflow.id} workflow={workflow} />
            ))}
            <li className="flex flex-col rounded-container border border-border bg-surface p-4">
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-[15px] font-semibold text-foreground">No match → your team</h2>
                <ToneChip tone="neutral">System</ToneChip>
              </div>
              <p className="mt-1.5 text-[13px] leading-5 text-text-secondary">
                Messages no workflow picks up stay in your inbox for a person to answer.
              </p>
              <div className="h-4" />
              <div className="mt-auto flex items-center justify-between gap-3 border-t border-border pt-3 text-[12.5px] tabular-nums text-text-secondary">
                <span>{data.routing.unmatched_7d} {data.routing.unmatched_7d === 1 ? "message" : "messages"}</span>
                <Link href="/app/inbox" className="font-medium text-primary hover:underline">Open inbox</Link>
              </div>
            </li>
          </ul>
        </div>
      ) : null}
    </div>
  );
}
