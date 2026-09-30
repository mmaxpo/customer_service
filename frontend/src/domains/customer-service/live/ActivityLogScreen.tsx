"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Loader2 } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";

import { formatDay, formatTime, humanize } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import { studioApi, type StudioWorkflow } from "../automation/api";
import { LiveHeader } from "./LiveHeader";
import { liveApi, type ActivityRow, type Outcome } from "./api";

const OUTCOMES: Record<Outcome, { label: string; tone: "neutral" | "attention" | "failure" | "commerce" }> = {
  answered: { label: "Answered", tone: "commerce" },
  handed_over: { label: "Handed to your team", tone: "attention" },
  failed: { label: "Failed", tone: "failure" },
  running: { label: "Running", tone: "neutral" },
  waiting_approval: { label: "Waiting for approval", tone: "attention" },
};

const selectClass =
  "h-8 rounded-control border border-border bg-surface px-2 text-[13px] text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function Row({ row }: { row: ActivityRow }) {
  const outcome = OUTCOMES[row.outcome];
  const body = (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <time className="text-[12px] tabular-nums text-text-secondary" dateTime={row.created_at}>
            {formatDay(row.created_at)} · {formatTime(row.created_at)}
          </time>
          <ToneChip tone={outcome.tone} className="shrink-0">{outcome.label}</ToneChip>
        </div>
        <p className="mt-1 truncate text-[13.5px] text-foreground">
          {row.customer_message ? <>&ldquo;{row.customer_message}&rdquo;</> : <span className="text-text-secondary">Started from the inbox</span>}
        </p>
        <p className="mt-0.5 text-[12.5px] text-text-secondary">
          {row.workflow_name ?? "Workflow"}
          {row.version ? ` · v${row.version}` : ""}
          {row.channel ? ` · ${humanize(row.channel)}` : ""}
          {row.attempts > 1 ? ` · tried ${row.attempts} times` : ""}
        </p>
        {row.reason ? <p className="mt-0.5 text-[12.5px] text-foreground">{row.reason}</p> : null}
      </div>
      {row.run_id ? <ChevronRight size={16} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden /> : null}
    </>
  );
  const className = "flex items-start gap-3 px-4 py-3";
  return (
    <li>
      {row.run_id ? (
        <Link
          href={`/app/workflows/runs/${row.run_id}`}
          className={`${className} transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus`}
        >
          {body}
        </Link>
      ) : (
        <div className={className}>{body}</div>
      )}
    </li>
  );
}

export default function ActivityLogScreen() {
  const [days, setDays] = useState(7);
  const [outcome, setOutcome] = useState<Outcome | "">("");
  const [workflowId, setWorkflowId] = useState("");
  const [workflows, setWorkflows] = useState<StudioWorkflow[]>([]);
  const [rows, setRows] = useState<ActivityRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    studioApi.overview().then((overview) => setWorkflows(overview.workflows)).catch(() => setWorkflows([]));
  }, []);

  useEffect(() => {
    setRows(null);
    setError(null);
    liveApi
      .activity({ days, outcome: outcome || undefined, workflowId: workflowId || undefined })
      .then(setRows)
      .catch((err) => setError(apiErrorMessage(err, "Could not load the activity log.")));
  }, [days, outcome, workflowId]);

  return (
    <div className="mx-auto max-w-5xl">
      <LiveHeader description="Every conversation an automation handled, what happened, and why." />

      <div className="mb-3 flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="activity-days">Period</label>
        <select id="activity-days" value={days} onChange={(e) => setDays(Number(e.target.value))} className={selectClass}>
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
        <label className="sr-only" htmlFor="activity-outcome">Outcome</label>
        <select id="activity-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome | "")} className={selectClass}>
          <option value="">All outcomes</option>
          {(Object.keys(OUTCOMES) as Outcome[]).map((key) => (
            <option key={key} value={key}>{OUTCOMES[key].label}</option>
          ))}
        </select>
        <label className="sr-only" htmlFor="activity-workflow">Workflow</label>
        <select id="activity-workflow" value={workflowId} onChange={(e) => setWorkflowId(e.target.value)} className={selectClass}>
          <option value="">All workflows</option>
          {workflows.map((workflow) => (
            <option key={workflow.id} value={workflow.id}>{workflow.name}</option>
          ))}
        </select>
      </div>

      {error ? <p role="alert" className="text-[13px] text-danger">{error}</p> : null}
      {!rows && !error ? (
        <p className="flex items-center gap-2 text-[13.5px] text-text-secondary">
          <Loader2 size={15} className="animate-spin" aria-hidden /> Loading…
        </p>
      ) : null}
      {rows && !rows.length ? (
        <p className="rounded-container border border-border bg-surface px-4 py-6 text-center text-[13.5px] text-text-secondary">
          No automated conversations match these filters.
        </p>
      ) : null}
      {rows?.length ? (
        <ul className="divide-y divide-border rounded-container border border-border bg-surface">
          {rows.map((row, index) => <Row key={row.run_id ?? `${row.created_at}-${index}`} row={row} />)}
        </ul>
      ) : null}
    </div>
  );
}
