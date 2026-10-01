"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";

import { ToneChip } from "../inbox/case/parts";
import { AskBar } from "./AskBar";
import { AutomationHeader } from "./AutomationHeader";
import { NewWorkflowDraft } from "./NewWorkflowDraft";
import { UnansweredTopics } from "./UnansweredTopics";
import { WorkflowCard } from "./WorkflowCard";
import { studioApi, type StudioOverview, type WorkflowDraft } from "./api";

export default function WorkflowsScreen() {
  const [data, setData] = useState<StudioOverview | null>(null);
  const [reviewCount, setReviewCount] = useState<number>();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<WorkflowDraft | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = () =>
    studioApi.overview().then(setData).catch((err) => setError(apiErrorMessage(err, "Could not load workflows.")));

  // "Review draft" on a suggestion (here, or from another page via ?new=...).
  const draftFrom = (request: string) => {
    setDraft(null);
    setNotice("TCOS is drafting a workflow for this…");
    window.scrollTo({ top: 0 });
    studioApi.draftWorkflow(request)
      .then((next) => { setDraft(next); setNotice(null); })
      .catch((err) => setNotice(apiErrorMessage(err, "TCOS could not draft this workflow.")));
  };

  useEffect(() => {
    void load();
    const request = new URLSearchParams(window.location.search).get("new");
    if (request) {
      window.history.replaceState(null, "", window.location.pathname);
      draftFrom(request);
    }
    studioApi.reviewQueue().then((runs) => setReviewCount(runs.length)).catch(() => {});
  }, []);

  const live = data?.workflows.filter((w) => w.enabled).length ?? 0;

  return (
    <div className="mx-auto max-w-6xl">
      <AutomationHeader
        title="Workflows"
        description="Every customer message goes to the workflow that fits. Anything that doesn't fit goes to your team."
        reviewCount={reviewCount}
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

          <AskBar workflows={data.workflows} onDraft={(next) => { setDraft(next); setNotice(null); }} />
          {draft ? (
            <NewWorkflowDraft
              key={draft.name}
              draft={draft}
              onDiscard={() => setDraft(null)}
              onSaved={() => { setDraft(null); setNotice("Saved. The new workflow is switched off: check its steps, then turn it on."); void load(); }}
            />
          ) : null}
          {notice ? <p role="status" className="text-[13px] text-commerce-accent">{notice}</p> : null}

          <UnansweredTopics title="Questions your workflows don't answer yet" onReview={draftFrom} />

          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.workflows.map((workflow) => (
              <WorkflowCard key={workflow.id} workflow={workflow} onChanged={() => void load()} />
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
                <Link href="/app/inbox?view=unanswered" className="font-medium text-primary hover:underline">See them in the inbox</Link>
              </div>
            </li>
          </ul>
        </div>
      ) : null}
    </div>
  );
}
