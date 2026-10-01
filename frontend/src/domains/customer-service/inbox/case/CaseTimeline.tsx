"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronRight, LoaderCircle, StickyNote } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import type { AutomationActivityEvent } from "@/domains/customer-service/model";
import { apiErrorMessage, apiJson } from "@/platform/api/client";
import { cn } from "@/platform/utils";

import { formatDay, formatTime } from "./format";
import { ActorAvatar, ToneChip } from "./parts";
import {
  buildTimeline,
  type Evidence,
  type TimelineEntry,
  type TimelineEvent,
} from "./timeline";

type Props = {
  conversationId: string;
  customerName: string | null;
  items: AutomationActivityEvent[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
};

type Translation = {
  language: string | null;
  translated: boolean;
  translations: { original: string; text: string }[];
};

const actorName = (entry: { actor: string }, customerName: string | null) =>
  entry.actor === "customer" ? customerName ?? "Customer"
    : entry.actor === "tajeran" ? "Tajeran"
      : entry.actor === "teammate" ? "Teammate"
        : entry.actor === "workflow" ? "Workflow" : "System";

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  return (
    <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-[12px]">
      {evidence.map((item) => (
        <div key={item.label} className="contents">
          <dt className="text-text-secondary">{item.label}</dt>
          <dd className="text-foreground">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Disclosure({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-0.5">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-0.5 rounded-control text-[12px] font-medium text-text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <ChevronRight size={13} className={cn("transition-transform", open && "rotate-90")} aria-hidden />
        {label}
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden pl-4"
          >
            {children}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function EventRow({ event, customerName, nested = false }: { event: TimelineEvent; customerName: string | null; nested?: boolean }) {
  const hasMore = !!event.evidence?.length;
  return (
    <div className="flex gap-3">
      <div className="flex w-6 shrink-0 justify-center pt-px">
        {nested ? <span className="mt-2 h-1 w-1 rounded-full bg-border" aria-hidden /> : <ActorAvatar actor={event.actor} size={20} />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <p className="min-w-0 text-[13px] leading-5 text-foreground">
            <span className="sr-only">{actorName(event, customerName)}: </span>
            {event.title}
            {event.status ? (
              <ToneChip tone={event.status.tone} className="ml-2 align-[1px]">
                {event.status.running ? <LoaderCircle size={11} className="animate-spin" aria-hidden /> : null}
                {event.status.label}
              </ToneChip>
            ) : null}
          </p>
          <time className="shrink-0 pt-px text-[11px] tabular-nums text-text-secondary" dateTime={event.at}>
            {formatTime(event.at)}
          </time>
        </div>
        {event.detail ? <p className="mt-0.5 text-[12.5px] leading-5 text-text-secondary">{event.detail}</p> : null}
        {hasMore ? (
          <Disclosure label="Evidence">
            <EvidenceList evidence={event.evidence!} />
          </Disclosure>
        ) : null}
      </div>
    </div>
  );
}

function EntryView({ entry, customerName, translations }: { entry: TimelineEntry; customerName: string | null; translations: Map<string, string> }) {
  if (entry.kind === "message") {
    const fromCustomer = entry.actor === "customer";
    const translated = translations.get(entry.body.trim());
    return (
      <div className="flex gap-3">
        <div className="flex w-6 shrink-0 justify-center pt-0.5">
          <ActorAvatar actor={entry.actor} name={fromCustomer ? customerName : null} size={24} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-[13px] font-semibold text-foreground">
              {actorName(entry, customerName)}
              {entry.aiAssisted ? <span className="ml-2 text-[11px] font-medium text-ai-accent">Drafted with Tajeran</span> : null}
            </p>
            <time className="shrink-0 text-[11px] tabular-nums text-text-secondary" dateTime={entry.at}>
              {formatTime(entry.at)}
            </time>
          </div>
          <div
            className={cn(
              "mt-1 whitespace-pre-wrap rounded-container px-3 py-2 text-[14px] leading-6",
              "border text-foreground",
              fromCustomer
                ? "border-border bg-muted"
                : entry.actor === "tajeran"
                  ? "border-ai-100 bg-ai-50"
                  : "border-border border-l-2 border-l-primary bg-surface",
            )}
          >
            {entry.body}
            {translated ? (
              <p className="mt-2 border-t border-border pt-2 text-[13.5px] text-text-secondary">
                <span className="mr-1.5 text-[11px] font-medium uppercase tracking-wide">Translation</span>
                {translated}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  if (entry.kind === "note") {
    return (
      <div className="flex gap-3">
        <div className="flex w-6 shrink-0 justify-center pt-0.5 text-text-secondary">
          <StickyNote size={16} strokeWidth={1.75} aria-hidden />
        </div>
        <div className="min-w-0 flex-1 rounded-container border border-warn-100 border-l-2 border-l-warning bg-warn-50 px-3 py-2">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-[12px] font-semibold text-text-secondary">Internal note</p>
            <time className="text-[11px] tabular-nums text-text-secondary" dateTime={entry.at}>{formatTime(entry.at)}</time>
          </div>
          <p className="mt-0.5 whitespace-pre-wrap text-[13px] leading-5 text-foreground">{entry.body}</p>
        </div>
      </div>
    );
  }

  if (entry.kind === "event") return <EventRow event={entry} customerName={customerName} />;

  if (entry.kind === "collapsed") {
    return (
      <div className="flex gap-3">
        <div className="flex w-6 shrink-0 justify-center pt-px"><ActorAvatar actor="tajeran" size={20} /></div>
        <div className="min-w-0 flex-1">
          <Disclosure label={entry.title}>
            <div className="mt-1.5 space-y-2">
              {entry.events.map((event) => <EventRow key={event.id} event={event} customerName={customerName} nested />)}
            </div>
          </Disclosure>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="flex w-6 shrink-0 justify-center pt-px"><ActorAvatar actor="workflow" size={20} /></div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <p className="text-[13px] leading-5 text-foreground">
            Ran workflow: {entry.title}
            {entry.status ? (
              <ToneChip tone={entry.status.tone} className="ml-2 align-[1px]">
                {entry.status.running ? <LoaderCircle size={11} className="animate-spin" aria-hidden /> : null}
                {entry.status.label}
              </ToneChip>
            ) : null}
          </p>
          <time className="shrink-0 pt-px text-[11px] tabular-nums text-text-secondary" dateTime={entry.at}>{formatTime(entry.at)}</time>
        </div>
        <Link
          href={`/app/workflows/runs/${entry.runId}`}
          className="mt-0.5 inline-block rounded-control text-[12px] font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          See what happened
        </Link>
      </div>
    </div>
  );
}

export function CaseTimeline({ conversationId, customerName, items, loading, error, onRetry }: Props) {
  const entries = useMemo(() => (items ? buildTimeline(items) : []), [items]);
  const activitySummary = useMemo(() => ({
    messages: entries.filter((entry) => entry.kind === "message").length,
    notes: entries.filter((entry) => entry.kind === "note").length,
    automations: entries.filter((entry) => entry.kind === "run" || entry.kind === "event" || entry.kind === "collapsed").length,
  }), [entries]);
  const scroller = useRef<HTMLDivElement>(null);
  const previousCount = useRef(0);
  // Translation of the conversation's messages, on request (one AI call).
  const [translation, setTranslation] = useState<Translation | null>(null);
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);
  const translations = useMemo(
    () => new Map((translation?.translations ?? []).map((item) => [item.original.trim(), item.text])),
    [translation],
  );

  useLayoutEffect(() => {
    previousCount.current = 0;
    setTranslation(null);
    setTranslateError(null);
  }, [conversationId]);

  async function translate() {
    setTranslating(true);
    setTranslateError(null);
    try {
      setTranslation(
        await apiJson<Translation>(`/api/customer-service/studio/conversations/${conversationId}/translate`, { method: "POST" }),
      );
    } catch (err) {
      setTranslateError(apiErrorMessage(err, "Could not translate this conversation."));
    } finally {
      setTranslating(false);
    }
  }

  useEffect(() => {
    const node = scroller.current;
    if (!node || entries.length === 0) return;
    const firstRender = previousCount.current === 0;
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 160;
    if (firstRender || (entries.length > previousCount.current && nearBottom)) {
      node.scrollTo({ top: node.scrollHeight, behavior: firstRender ? "auto" : "smooth" });
    }
    previousCount.current = entries.length;
  }, [entries.length, conversationId]);

  let lastDay = "";

  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-busy={loading}>
      <div className="mx-auto w-full max-w-3xl px-4 py-5 sm:px-6">
        {items && entries.length ? (
          <div className="mb-5 flex flex-wrap items-center gap-2 rounded-container border border-border bg-surface px-3 py-2.5 text-[12px]">
            <span className="mr-1 font-semibold text-foreground">Case activity</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-text-secondary">{activitySummary.messages} messages</span>
            {activitySummary.notes ? <span className="rounded-full bg-muted px-2 py-0.5 text-text-secondary">{activitySummary.notes} notes</span> : null}
            {activitySummary.automations ? <span className="rounded-full bg-ai-50 px-2 py-0.5 text-ai-accent">{activitySummary.automations} Tajeran events</span> : null}
            <span className="ml-auto text-text-secondary">
              {translation ? (
                translation.translated
                  ? `Customer wrote in ${translation.language ?? "another language"} · translated`
                  : `Customer wrote in ${translation.language ?? "your language"} · no translation needed`
              ) : (
                <button type="button" onClick={() => void translate()} disabled={translating} className="font-medium text-primary hover:underline disabled:opacity-60">
                  {translating ? "Translating…" : "Translate conversation"}
                </button>
              )}
            </span>
            {translateError ? <p role="alert" className="w-full text-danger">{translateError}</p> : null}
          </div>
        ) : null}
        {error && !items ? (
          <p className="text-sm text-danger">
            {error}{" "}
            <button type="button" onClick={onRetry} className="font-medium underline underline-offset-2">Try again</button>
          </p>
        ) : null}

        {!items && loading ? (
          <div className="space-y-5" aria-hidden>
            {[0, 1, 2].map((row) => (
              <div key={row} className="flex gap-3">
                <div className="h-6 w-6 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-32 rounded bg-muted" />
                  <div className="h-12 rounded-container bg-muted" />
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {items && entries.length === 0 ? (
          <p className="text-sm text-text-secondary">No activity on this case yet.</p>
        ) : null}

        <ol key={conversationId} className="space-y-4">
          <AnimatePresence initial={false}>
            {entries.map((entry) => {
              const day = formatDay(entry.at);
              const showDay = day !== lastDay;
              lastDay = day;
              return (
                <motion.li
                  key={entry.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                >
                  {showDay ? (
                    <div className="mb-4 flex items-center gap-3 text-[11px] font-medium text-text-secondary">
                      <span className="h-px flex-1 bg-border" aria-hidden />
                      {day}
                      <span className="h-px flex-1 bg-border" aria-hidden />
                    </div>
                  ) : null}
                  <EntryView entry={entry} customerName={customerName} translations={translations} />
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ol>
      </div>
    </div>
  );
}
