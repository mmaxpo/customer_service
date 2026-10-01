"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { apiJson, apiErrorMessage } from "@/platform/api/client";
import { topicLabel } from "@/domains/customer-service/model/topics";

import { formatDay } from "../inbox/case/format";

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

type Bucket = { label: string; value: number };

type Speed = {
  first_reply: {
    conversations: number;
    replied: number;
    median_seconds: number | null;
    buckets: Bucket[];
    target_minutes: number | null;
    within_target_rate: number | null;
  };
  resolution: { resolved: number; median_seconds: number | null; buckets: Bucket[] };
};

type Tickets = {
  created: number;
  open: number;
  pending: number;
  resolved: number;
  oldest_open_seconds: number | null;
  backlog: Bucket[];
  by_channel: Bucket[];
};

export type Insights = {
  days: number;
  tickets: Tickets;
  automation: Automation;
  automation_previous: Automation;
  rating: Rating;
  rating_previous: Rating;
  answer_feedback: { helpful: number; not_helpful: number };
  top_topics: { topic: string; conversations: number }[];
  speed: Speed;
  speed_previous: Speed;
  lowest_rated: { conversation_id: string; score: number; comment: string | null; answered_at: string; customer_name: string | null }[];
};

export function useInsights(days: number) {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiJson<Insights>(`/api/customer-service/studio/desk/insights?days=${days}`)
      .then(setData)
      .catch((err) => setError(apiErrorMessage(err, "Could not load this report.")))
      .finally(() => setLoading(false));
  }, [days]);
  useEffect(load, [load]);
  return { data, error, loading, reload: load };
}

// No hint when there is nothing earlier to compare with: the page says so once.
function change(current: number | null, previous: number | null, unit: string, days: number) {
  if (current === null) return "No data yet";
  if (previous === null) return undefined;
  const diff = Math.round((current - previous) * 10) / 10;
  if (diff === 0) return `Same as the ${days} days before`;
  return `${diff > 0 ? "+" : ""}${diff}${unit} vs the ${days} days before`;
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded border border-border bg-surface px-4 py-4">
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="mt-2 text-[27px] font-semibold tracking-tight text-foreground">{value}</p>
      {hint ? <p className="mt-1 text-xs text-text-secondary">{hint}</p> : null}
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

const percent = (value: number | null) => (value === null ? "—" : `${value}%`);

export function AutomationReport({ data }: { data: Insights }) {
  const { days } = data;
  const { automation: now, automation_previous: before, answer_feedback: feedback } = data;

  return (
    <>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Answered automatically" value={percent(now.answered_rate)} hint={change(now.answered_rate, before.answered_rate, " pts", days)} />
        <Stat label="Handed to your team" value={percent(now.handed_over_rate)} hint={change(now.handed_over_rate, before.handed_over_rate, " pts", days)} />
        <Stat label="Failed" value={percent(now.failed_rate)} hint={change(now.failed_rate, before.failed_rate, " pts", days)} />
        <Stat label="Conversations handled" value={String(now.total)} hint={change(now.total, before.total || null, "", days)} />
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

function duration(seconds: number | null) {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${Math.round(seconds / 360) / 10} hrs`;
  return `${Math.round(seconds / 8640) / 10} days`;
}

function speedChange(current: number | null, previous: number | null, days: number) {
  if (current === null) return "No data yet";
  if (previous === null) return undefined;
  if (duration(current) === duration(previous)) return `Same as the ${days} days before`;
  return `${current < previous ? "Faster" : "Slower"} than the ${days} days before (${duration(previous)})`;
}

const channelLabel = (channel: string) => {
  const text = channel.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

export function TicketsReport({ data }: { data: Insights }) {
  const { tickets, automation } = data;

  return (
    <>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <Stat label="New tickets" value={String(tickets.created)} hint="In this period" />
        <Stat label="Open" value={String(tickets.open)} hint="Right now" />
        <Stat label="Pending" value={String(tickets.pending)} hint="Right now" />
        <Stat label="Resolved" value={String(tickets.resolved)} hint="In this period" />
        <Stat label="Oldest open ticket" value={duration(tickets.oldest_open_seconds)} hint={tickets.oldest_open_seconds === null ? "Nothing is waiting" : "Since it was opened"} />
        <Stat label="Answered automatically" value={percent(automation.answered_rate)} hint={`${automation.answered} of ${automation.total} conversations`} />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded border border-border bg-surface p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">Backlog age</h2>
              <p className="mt-1 text-sm text-text-secondary">How long open and pending tickets have been waiting.</p>
            </div>
            <Link href="/app/inbox" className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary">
              Open Inbox <ArrowUpRight size={14} />
            </Link>
          </div>
          {tickets.open + tickets.pending ? (
            <div className="mt-5"><Bars rows={tickets.backlog} /></div>
          ) : (
            <Empty text="No open or pending tickets." />
          )}
        </section>
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Tickets by channel</h2>
          <p className="mt-1 text-sm text-text-secondary">Where new tickets came from.</p>
          {tickets.by_channel.length ? (
            <div className="mt-5">
              <Bars rows={tickets.by_channel.map((row) => ({ label: channelLabel(row.label), value: row.value }))} />
            </div>
          ) : (
            <Empty text="No new tickets in this period." />
          )}
        </section>
      </div>
    </>
  );
}

export function SpeedReport({ data }: { data: Insights }) {
  const { days } = data;
  const { first_reply: reply, resolution } = data.speed;
  const before = data.speed_previous;

  return (
    <>
      <div className={`mt-5 grid gap-3 sm:grid-cols-2 ${reply.target_minutes ? "xl:grid-cols-5" : "xl:grid-cols-4"}`}>
        <Stat label="First reply, median" value={duration(reply.median_seconds)} hint={speedChange(reply.median_seconds, before.first_reply.median_seconds, days)} />
        <Stat label="Conversations replied to" value={`${reply.replied} of ${reply.conversations}`} hint="By the bot or a team member" />
        {reply.target_minutes ? (
          <Stat
            label="Answered within target"
            value={percent(reply.within_target_rate)}
            hint={`First reply within ${reply.target_minutes} min, during business hours`}
          />
        ) : null}
        <Stat label="Time to resolve, median" value={duration(resolution.median_seconds)} hint={speedChange(resolution.median_seconds, before.resolution.median_seconds, days)} />
        <Stat label="Tickets resolved" value={String(resolution.resolved)} hint="In this period" />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Time to first reply</h2>
          <p className="mt-1 text-sm text-text-secondary">From the customer's first message to the first answer.</p>
          {reply.conversations ? (
            <div className="mt-5"><Bars rows={reply.buckets} /></div>
          ) : (
            <Empty text="No new conversations in this period." />
          )}
        </section>
        <section className="rounded border border-border bg-surface p-5">
          <h2 className="font-semibold">Time to resolve</h2>
          <p className="mt-1 text-sm text-text-secondary">From when a ticket was opened to when it was resolved.</p>
          {resolution.resolved ? (
            <div className="mt-5"><Bars rows={resolution.buckets} /></div>
          ) : (
            <Empty text="No tickets were resolved in this period." />
          )}
        </section>
      </div>
    </>
  );
}

export function SatisfactionReport({ data }: { data: Insights }) {
  const { days } = data;
  const { rating, rating_previous: before } = data;

  return (
    <>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <Stat
          label="Customer rating"
          value={rating.average === null ? "—" : `${rating.average} / 5`}
          hint={change(rating.average, before.average, "", days)}
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
