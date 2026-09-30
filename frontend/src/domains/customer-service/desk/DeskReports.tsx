"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { apiJson, apiErrorMessage } from "@/platform/api/client";
import { topicLabel } from "@/domains/customer-service/model/topics";

import { formatDay } from "../inbox/case/format";

// The Desk header says "Last 30 days"; these reports use the same period.
const DAYS = 30;

type Automation = {
  total: number;
  answered: number;
  handed_over: number;
  failed: number;
  answered_rate: number | null;
  handed_over_rate: number | null;
  failed_rate: number | null;
};

type Rating = { responses: number; average: number | null; distribution: Record<string, number> };

type Insights = {
  automation: Automation;
  automation_previous: Automation;
  rating: Rating;
  rating_previous: Rating;
  answer_feedback: { helpful: number; not_helpful: number };
  top_topics: { topic: string; conversations: number }[];
  lowest_rated: { conversation_id: string; score: number; comment: string | null; answered_at: string; customer_name: string | null }[];
};

function useInsights() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiJson<Insights>(`/api/customer-service/studio/desk/insights?days=${DAYS}`)
      .then(setData)
      .catch((err) => setError(apiErrorMessage(err, "Could not load this report.")));
  }, []);
  return { data, error };
}

function change(current: number | null, previous: number | null, unit: string) {
  if (current === null) return "No data yet";
  if (previous === null) return "No earlier data to compare";
  const diff = Math.round((current - previous) * 10) / 10;
  if (diff === 0) return "Same as the 30 days before";
  return `${diff > 0 ? "+" : ""}${diff}${unit} vs the 30 days before`;
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded border border-border bg-surface px-4 py-4">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="mt-2 text-[27px] font-semibold tracking-tight text-foreground">{value}</p>
      <p className="mt-1 text-xs text-text-secondary">{hint}</p>
    </div>
  );
}

function Bars({ rows }: { rows: { label: string; value: number }[] }) {
  const max = Math.max(1, ...rows.map((row) => row.value));
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label} className="grid grid-cols-[9rem_1fr_2.5rem] items-center gap-3 text-sm">
          <span className="truncate text-text-secondary">{row.label}</span>
          <div className="h-5 bg-muted">
            <div className="h-full bg-primary/70" style={{ width: row.value ? `${Math.max(2, (row.value / max) * 100)}%` : 0 }} />
          </div>
          <span className="text-right text-xs font-semibold tabular-nums text-text-secondary">{row.value}</span>
        </div>
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="mt-5 rounded border border-dashed border-border bg-muted/40 px-4 py-6 text-center text-sm text-text-secondary">{text}</p>;
}

function Status({ error }: { error: string | null }) {
  return error
    ? <p role="alert" className="mt-5 text-sm text-danger">{error}</p>
    : <div className="mt-5 h-40 animate-pulse rounded bg-muted" />;
}

const percent = (value: number | null) => (value === null ? "—" : `${value}%`);

export function AutomationReport() {
  const { data, error } = useInsights();
  if (!data) return <Status error={error} />;
  const { automation: now, automation_previous: before, answer_feedback: feedback } = data;

  return (
    <>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Answered automatically" value={percent(now.answered_rate)} hint={change(now.answered_rate, before.answered_rate, " pts")} />
        <Stat label="Handed to your team" value={percent(now.handed_over_rate)} hint={change(now.handed_over_rate, before.handed_over_rate, " pts")} />
        <Stat label="Failed" value={percent(now.failed_rate)} hint={change(now.failed_rate, before.failed_rate, " pts")} />
        <Stat label="Conversations handled" value={String(now.total)} hint={change(now.total, before.total || null, "")} />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Top topics</h2>
          <p className="mt-1 text-sm text-text-secondary">What customers wrote about.</p>
          {data.top_topics.length ? (
            <div className="mt-5">
              <Bars rows={data.top_topics.map((t) => ({ label: topicLabel(t.topic) ?? t.topic, value: t.conversations }))} />
            </div>
          ) : (
            <Empty text="No customer messages in this period." />
          )}
        </section>
        <section className="rounded border border-border bg-surface p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">Customers' view of automated answers</h2>
              <p className="mt-1 text-sm text-text-secondary">From "Was this helpful?" in the chat.</p>
            </div>
            <Link href="/app/live/activity" className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary">
              Activity log <ArrowUpRight size={14} />
            </Link>
          </div>
          {feedback.helpful + feedback.not_helpful ? (
            <div className="mt-5">
              <Bars rows={[{ label: "Helpful 👍", value: feedback.helpful }, { label: "Not helpful 👎", value: feedback.not_helpful }]} />
              <p className="mt-4 text-sm text-text-secondary">
                Answers marked not helpful are added to{" "}
                <Link href="/app/workflows/review" className="font-medium text-primary">Needs review</Link>.
              </p>
            </div>
          ) : (
            <Empty text="No feedback on answers yet." />
          )}
        </section>
      </div>
    </>
  );
}

export function SatisfactionReport() {
  const { data, error } = useInsights();
  if (!data) return <Status error={error} />;
  const { rating, rating_previous: before } = data;

  return (
    <>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Stat
          label="Customer rating"
          value={rating.average === null ? "—" : `${rating.average} / 5`}
          hint={change(rating.average, before.average, "")}
        />
        <Stat label="Ratings received" value={String(rating.responses)} hint="Asked once per chat, after an answer" />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Ratings</h2>
          {rating.responses ? (
            <div className="mt-5">
              <Bars rows={[5, 4, 3, 2, 1].map((score) => ({ label: `${score} out of 5`, value: rating.distribution[score] ?? 0 }))} />
            </div>
          ) : (
            <Empty text="No ratings yet. Customers are asked to rate a chat after they get an answer." />
          )}
        </section>
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Lowest-rated chats</h2>
          <p className="mt-1 text-sm text-text-secondary">Rated 3 or lower. Open one to see what happened.</p>
          {data.lowest_rated.length ? (
            <ul className="mt-4 divide-y divide-border">
              {data.lowest_rated.map((row) => (
                <li key={row.conversation_id}>
                  <Link href={`/app/inbox?conversation=${row.conversation_id}`} className="flex items-start justify-between gap-3 py-3 text-sm hover:bg-muted/60">
                    <span className="min-w-0">
                      <span className="font-medium">{row.customer_name ?? "Customer"}</span>
                      {row.comment ? <span className="mt-0.5 block truncate text-text-secondary">&ldquo;{row.comment}&rdquo;</span> : null}
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block font-semibold tabular-nums">{row.score} / 5</span>
                      <span className="text-xs text-text-secondary">{formatDay(row.answered_at)}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <Empty text="No low ratings in this period." />
          )}
        </section>
      </div>
    </>
  );
}
