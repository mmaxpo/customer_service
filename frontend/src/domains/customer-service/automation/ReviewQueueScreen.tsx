"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";

import { formatDay, formatTime } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { AutomationHeader } from "./AutomationHeader";
import { studioApi, type ReviewReason, type RunSummary } from "./api";

const reasonChip: Record<ReviewReason, { label: string; tone: "attention" | "failure" | "neutral" }> = {
  flagged: { label: "Marked as wrong", tone: "attention" },
  failed: { label: "Run failed", tone: "failure" },
  handed_over: { label: "Handed to your team", tone: "neutral" },
};

export default function ReviewQueueScreen() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    studioApi.reviewQueue().then(setRuns).catch((err) => setError(apiErrorMessage(err, "Could not load the review queue.")));
  }, []);

  return (
    <div className="mx-auto max-w-6xl">
      <AutomationHeader
        title="Needs review"
        description="Conversations where a workflow failed, handed over to your team, or someone marked an answer as wrong."
        reviewCount={runs?.length}
      />

      {error ? <p role="alert" className="text-[13.5px] text-danger">{error}</p> : null}
      {!runs && !error ? (
        <p className="flex items-center gap-2 text-[13.5px] text-text-secondary">
          <Loader2 size={15} className="animate-spin" aria-hidden /> Loading…
        </p>
      ) : null}
      {runs && !runs.length ? (
        <p className="rounded-container border border-border bg-surface p-6 text-center text-[13.5px] text-text-secondary">
          Nothing to review from the last 30 days.
        </p>
      ) : null}

      {runs?.length ? (
        <ul className="divide-y divide-border overflow-hidden rounded-container border border-border bg-surface">
          {runs.map((run) => (
            <li key={run.run_id}>
              <Link
                href={`/app/workflows/runs/${run.run_id}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium text-foreground">
                    {run.workflow_name ?? "Workflow run"}
                    {run.version ? <span className="text-text-secondary"> · v{run.version}</span> : null}
                  </p>
                  {run.customer_message ? (
                    <p className="mt-0.5 truncate text-[13px] text-text-secondary">&ldquo;{run.customer_message}&rdquo;</p>
                  ) : null}
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {run.review_reasons.map((reason) => (
                      <ToneChip key={reason} tone={reasonChip[reason].tone}>{reasonChip[reason].label}</ToneChip>
                    ))}
                  </div>
                </div>
                <span className="shrink-0 text-[12.5px] tabular-nums text-text-secondary">
                  {formatDay(run.created_at)} {formatTime(run.created_at)}
                </span>
                <ChevronRight size={16} className="shrink-0 text-text-secondary" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
