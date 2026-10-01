"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronRight, Loader2, TriangleAlert } from "lucide-react";

import { apiErrorMessage } from "@/platform/api/client";

import { formatShortAgo, formatTime, humanize } from "../inbox/case/format";
import { LiveHeader } from "./LiveHeader";
import { ReplyTargetChip } from "./ReplyTargetChip";
import { liveApi, type LiveNow } from "./api";

const REFRESH_MS = 30_000;

function waitingLabel(since: string) {
  const ago = formatShortAgo(since);
  return /^\d/.test(ago) ? `Waiting ${ago}` : ago === "now" ? "Just now" : `Waiting since ${ago}`;
}

function SectionTitle({ children, count }: { children: React.ReactNode; count?: number }) {
  return (
    <h2 className="mb-2 flex items-center gap-2 text-[14px] font-semibold text-foreground">
      {children}
      {count !== undefined ? <span className="text-[12.5px] font-normal tabular-nums text-text-secondary">{count}</span> : null}
    </h2>
  );
}

export default function LiveNowScreen() {
  const [data, setData] = useState<LiveNow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      liveApi
        .now()
        .then((next) => alive && (setData(next), setError(null)))
        .catch((err) => alive && setError(apiErrorMessage(err, "Could not load what's happening now.")));
    void load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <LiveHeader description="What needs your attention right now. Updates every 30 seconds." />

      {error ? <p role="alert" className="mb-3 text-[13px] text-danger">{error}</p> : null}
      {!data && !error ? (
        <p className="flex items-center gap-2 text-[13.5px] text-text-secondary">
          <Loader2 size={15} className="animate-spin" aria-hidden /> Loading…
        </p>
      ) : null}

      {data ? (
        <div className="space-y-7">
          <dl className="grid grid-cols-3 divide-x divide-border rounded-container border border-border bg-surface">
            {[
              { label: "Waiting for a person", value: data.waiting_for_person.length },
              { label: "Waiting for approval", value: data.approvals_waiting.length },
              { label: "Automations running", value: data.running },
            ].map((stat) => (
              <div key={stat.label} className="px-4 py-3">
                <dt className="text-[12.5px] text-text-secondary">{stat.label}</dt>
                <dd className="mt-0.5 text-[20px] font-semibold tabular-nums text-foreground">{stat.value}</dd>
              </div>
            ))}
          </dl>

          {data.problems.length ? (
            <section aria-labelledby="problems">
              <SectionTitle>
                <span id="problems">Problems in the last 24 hours</span>
              </SectionTitle>
              <ul className="divide-y divide-border rounded-container border border-warning/40 bg-warning/5">
                {data.problems.map((problem) => (
                  <li key={problem.reason} className="flex items-start gap-3 px-4 py-3">
                    <TriangleAlert size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="text-[13.5px] font-medium text-foreground">{problem.reason}</p>
                      <p className="mt-0.5 text-[12.5px] text-text-secondary">
                        {problem.count} {problem.count === 1 ? "conversation" : "conversations"} · last at {formatTime(problem.last_at)}
                      </p>
                    </div>
                    {problem.example_run_id ? (
                      <Link href={`/app/workflows/runs/${problem.example_run_id}`} className="shrink-0 text-[13px] font-medium text-primary hover:underline">
                        See an example
                      </Link>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section aria-labelledby="waiting">
            <SectionTitle count={data.waiting_for_person.length}>
              <span id="waiting">Waiting for a person</span>
            </SectionTitle>
            {data.waiting_for_person.length ? (
              <ul className="divide-y divide-border rounded-container border border-border bg-surface">
                {data.waiting_for_person.map((item) => (
                  <li key={item.conversation_id}>
                    <Link
                      href={`/app/inbox?conversation=${item.conversation_id}`}
                      className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="flex flex-wrap items-center gap-x-2 text-[13.5px]">
                          <span className="font-medium text-foreground">{item.customer_name ?? "Customer"}</span>
                          <span className="text-[12px] text-text-secondary">{humanize(item.channel)}</span>
                          <ReplyTargetChip item={item} />
                        </p>
                        <p className="mt-0.5 truncate text-[13px] text-foreground">&ldquo;{item.last_customer_message}&rdquo;</p>
                        <p className="mt-0.5 text-[12.5px] text-text-secondary">{item.reason}</p>
                      </div>
                      <span className="shrink-0 text-[12.5px] font-medium tabular-nums text-warning">{waitingLabel(item.waiting_since)}</span>
                      <ChevronRight size={16} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-container border border-border bg-surface px-4 py-3 text-[13px] text-text-secondary">
                Nobody is waiting. Every open conversation has an answer.
              </p>
            )}
          </section>

          <section aria-labelledby="approvals">
            <SectionTitle count={data.approvals_waiting.length}>
              <span id="approvals">Waiting for approval</span>
            </SectionTitle>
            {data.approvals_waiting.length ? (
              <ul className="divide-y divide-border rounded-container border border-border bg-surface">
                {data.approvals_waiting.map((approval) => (
                  <li key={approval.id} className="flex items-center gap-3 px-4 py-3">
                    <p className="min-w-0 flex-1 truncate text-[13.5px] text-foreground">{approval.question ?? "An action needs your approval"}</p>
                    <span className="shrink-0 text-[12.5px] tabular-nums text-text-secondary">{waitingLabel(approval.created_at)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-container border border-border bg-surface px-4 py-3 text-[13px] text-text-secondary">No actions are waiting for approval.</p>
            )}
            {data.approvals_waiting.length ? (
              <Link href="/app/approvals" className="mt-2 inline-block text-[13px] font-medium text-primary hover:underline">Open Approvals</Link>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}
