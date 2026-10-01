"use client";

import { useMemo, useRef, useState } from "react";
import { Check, Search, SlidersHorizontal, Tag, X } from "lucide-react";
import { motion } from "motion/react";

import type { InboxFolder, InboxItem } from "@/domains/customer-service/model";
import { customerServiceApi } from "@/domains/customer-service/api";
import { apiErrorMessage } from "@/platform/api/client";
import { cn } from "@/platform/utils";

import { topicLabel } from "@/domains/customer-service/model/topics";
import { ReplyTargetChip } from "@/domains/customer-service/live/ReplyTargetChip";
import { useWaitingForPerson } from "@/domains/customer-service/live/useWaitingForPerson";

import { formatShortAgo, humanize, lower } from "../../case/format";

const FOLDERS: { value: InboxFolder; label: string }[] = [
  { value: "inbox", label: "Inbox" },
  { value: "snoozed", label: "Snoozed" },
  { value: "spam", label: "Spam" },
  { value: "all", label: "All" },
];

const URGENT = new Set(["high", "urgent"]);
const VIEWS = [
  { value: "all", label: "All cases" },
  { value: "unassigned", label: "Unassigned" },
  { value: "open", label: "Open" },
  { value: "pending", label: "Pending" },
  { value: "resolved", label: "Resolved" },
  { value: "priority", label: "Priority" },
] as const;

type QueueView = (typeof VIEWS)[number]["value"];

type Props = {
  items: InboxItem[];
  folder: InboxFolder;
  onFolderChange: (folder: InboxFolder) => void;
  selectedConversationId: string | null;
  onSelect: (conversationId: string) => void;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

function QueueRow({ item, selected, checked, onSelect, onToggle }: { item: InboxItem; selected: boolean; checked: boolean; onSelect: () => void; onToggle: () => void }) {
  const priority = lower(item.ticket?.priority);
  const ticketStatus = lower(item.ticket?.status);
  const title = item.customer_name || item.customer_email || "Unknown customer";
  const headline = item.subject || item.latest_message || "No messages yet";
  const preview = item.subject ? item.latest_message : null;
  const waiting = useWaitingForPerson()?.find((row) => row.conversation_id === item.conversation_id);

  return (
    <div className={cn("relative border-b border-border", selected && "bg-primary/[0.06]")}>
      <input
        type="checkbox"
        aria-label={`Select ${title}`}
        checked={checked}
        onChange={onToggle}
        className="absolute left-3 top-3.5 z-10 h-3.5 w-3.5 accent-[var(--color-primary)]"
      />
      <button
        type="button"
        data-conversation-id={item.conversation_id}
        onClick={onSelect}
        aria-current={selected ? "true" : undefined}
        className={cn(
        "relative block w-full px-4 py-2.5 pl-10 text-left transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus",
        selected ? "" : "hover:bg-muted/70",
        )}
      >
      {selected ? <span className="absolute inset-y-0 left-0 w-0.5 bg-primary" aria-hidden /> : null}
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate text-[13px] font-semibold text-foreground">{title}</span>
        <time className="shrink-0 text-[11px] tabular-nums text-text-secondary" dateTime={item.updated_at}>
          {formatShortAgo(item.updated_at)}
        </time>
      </div>
      <p className="mt-0.5 truncate text-[13px] text-foreground">{headline}</p>
      {preview ? <p className="truncate text-[12.5px] text-text-secondary">{preview}</p> : null}
      <div className="mt-1 flex min-w-0 items-center gap-2 text-[11.5px] text-text-secondary">
        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 font-medium text-[10.5px] text-text-secondary">{humanize(item.channel)}</span>
        {item.topic ? <span className="shrink-0 font-medium text-foreground/80">{topicLabel(item.topic)}</span> : null}
        {URGENT.has(priority) ? (
          <span className={cn("shrink-0 font-medium", priority === "urgent" ? "text-danger" : "text-warning")}>
            {humanize(priority)}
          </span>
        ) : null}
        {waiting ? <ReplyTargetChip item={waiting} /> : null}
        {ticketStatus && ticketStatus !== "open" ? <span className="shrink-0">{humanize(ticketStatus)}</span> : null}
        {item.tags.length ? <span className="truncate">{item.tags.slice(0, 2).join(", ")}</span> : null}
      </div>
      </button>
    </div>
  );
}

export function InboxQueue({ items, folder, onFolderChange, selectedConversationId, onSelect, loading, error, refresh }: Props) {
  const [query, setQuery] = useState("");
  const [view, setView] = useState<QueueView>("all");
  const [urgentOnly, setUrgentOnly] = useState(false);
  const [topic, setTopic] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkTag, setBulkTag] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((item) => {
      const ticketStatus = lower(item.ticket?.status || item.status);
      const priority = lower(item.ticket?.priority);
      if (view === "unassigned" && item.ticket?.assigned_to) return false;
      if (view === "open" && ticketStatus !== "open") return false;
      if (view === "pending" && ticketStatus !== "pending") return false;
      if (view === "resolved" && ticketStatus !== "resolved") return false;
      if (view === "priority" && !URGENT.has(priority)) return false;
      if (urgentOnly && !URGENT.has(lower(item.ticket?.priority))) return false;
      if (topic && item.topic !== topic) return false;
      if (!needle) return true;
      return [item.customer_name, item.customer_email, item.subject, item.latest_message, ...item.tags]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [items, query, urgentOnly, view, topic]);

  const topics = useMemo(
    () => [...new Set(items.map((item) => item.topic).filter((value): value is string => Boolean(value)))].sort(),
    [items],
  );

  const viewCounts = useMemo(() => {
    const counts: Record<QueueView, number> = {
      all: items.length,
      unassigned: items.filter((item) => !item.ticket?.assigned_to).length,
      open: items.filter((item) => lower(item.ticket?.status || item.status) === "open").length,
      pending: items.filter((item) => lower(item.ticket?.status || item.status) === "pending").length,
      resolved: items.filter((item) => lower(item.ticket?.status || item.status) === "resolved").length,
      priority: items.filter((item) => URGENT.has(lower(item.ticket?.priority))).length,
    };
    return counts;
  }, [items]);

  const moveSelection = (direction: 1 | -1) => {
    if (visible.length === 0) return;
    const index = visible.findIndex((item) => item.conversation_id === selectedConversationId);
    const next = visible[Math.min(visible.length - 1, Math.max(0, index + direction))];
    onSelect(next.conversation_id);
    listRef.current
      ?.querySelector<HTMLButtonElement>(`[data-conversation-id="${next.conversation_id}"]`)
      ?.focus();
  };

  const toggleSelected = (conversationId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(conversationId)) next.delete(conversationId);
      else next.add(conversationId);
      return next;
    });
  };

  const runBulk = async (action: "resolve" | "priority" | "tag") => {
    const chosen = items.filter((item) => selectedIds.has(item.conversation_id));
    if (!chosen.length || (action === "tag" && !bulkTag.trim())) return;
    setBulkBusy(true);
    setBulkError(null);
    try {
      await Promise.all(chosen.map((item) => {
        if (!item.ticket) return Promise.resolve();
        if (action === "resolve") return customerServiceApi.updateTicket(item.ticket.id, { status: "resolved" });
        if (action === "priority") return customerServiceApi.updateTicket(item.ticket.id, { priority: "high" });
        return customerServiceApi.addTag(item.conversation_id, bulkTag.trim());
      }));
      setSelectedIds(new Set());
      setBulkTag("");
      await refresh();
    } catch (err) {
      setBulkError(apiErrorMessage(err, "Could not update the selected tickets"));
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 space-y-2.5 border-b border-border bg-surface px-4 pb-2.5 pt-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[15px] font-semibold text-foreground">Tickets</h2>
          {!loading ? <span className="text-[12px] tabular-nums text-text-secondary">{visible.length} of {items.length}</span> : null}
        </div>
        <div className="flex gap-1.5">
          <label className="relative block min-w-0 flex-1">
            <span className="sr-only">Search conversations</span>
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" aria-hidden />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search customer, subject or message"
              className="h-8 w-full rounded-control border border-border bg-surface pl-8 pr-2 text-[13px] outline-none placeholder:text-text-secondary focus:border-focus focus:ring-2 focus:ring-focus/30"
            />
          </label>
          {topics.length ? (
            <select
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              aria-label="Topic"
              className="h-8 max-w-[8.5rem] shrink-0 rounded-control border border-border bg-surface px-1.5 text-[12.5px] text-foreground outline-none focus:border-focus focus:ring-2 focus:ring-focus/30"
            >
              <option value="">All topics</option>
              {topics.map((value) => (
                <option key={value} value={value}>{topicLabel(value)}</option>
              ))}
            </select>
          ) : null}
        </div>
        <div className="-mx-1 flex items-center gap-1 overflow-x-auto pb-0.5" role="tablist" aria-label="Ticket view">
          {VIEWS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="tab"
              aria-selected={view === option.value}
              onClick={() => setView(option.value)}
              className={cn(
                "shrink-0 rounded-control px-2 py-1 text-[11.5px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                view === option.value ? "bg-foreground text-background" : "text-text-secondary hover:bg-muted hover:text-foreground",
              )}
            >
              {option.label} <span className="ml-0.5 tabular-nums opacity-70">{viewCounts[option.value]}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between gap-2">
          <div role="tablist" aria-label="Inbox folder" className="flex gap-0.5">
            {FOLDERS.map((option) => (
              <button
                key={option.value}
                type="button"
                role="tab"
                aria-selected={folder === option.value}
                onClick={() => onFolderChange(option.value)}
                className={cn(
                  "rounded-control px-2 py-1 text-[12px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                  folder === option.value ? "bg-primary/[0.08] text-primary" : "text-text-secondary hover:bg-muted hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            role="checkbox"
            aria-checked={urgentOnly}
            onClick={() => setUrgentOnly((value) => !value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-control px-1.5 py-1 text-[12px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              urgentOnly ? "text-warning" : "text-text-secondary hover:text-foreground",
            )}
            >
            <SlidersHorizontal size={13} aria-hidden />
            <span
              aria-hidden
              className={cn(
                "flex h-3.5 w-3.5 items-center justify-center rounded-[3px] border",
                urgentOnly ? "border-warning bg-warning text-white" : "border-border bg-surface",
              )}
            >
              {urgentOnly ? <Check size={10} strokeWidth={3} /> : null}
            </span>
            Priority
          </button>
        </div>
      </div>

      <div
        className="min-h-0 flex-1 overflow-y-auto"
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "j") { event.preventDefault(); moveSelection(1); }
          if (event.key === "ArrowUp" || event.key === "k") { event.preventDefault(); moveSelection(-1); }
        }}
      >
        {selectedIds.size ? (
          <div className="sticky top-0 z-20 flex flex-wrap items-center gap-1.5 border-b border-border bg-surface px-3 py-2 shadow-sm">
            <span className="mr-auto text-[12px] font-medium text-foreground">{selectedIds.size} selected</span>
            <button type="button" disabled={bulkBusy} onClick={() => void runBulk("resolve")} className="rounded-control bg-muted px-2 py-1 text-[11.5px] font-medium text-foreground hover:bg-border">Resolve</button>
            <button type="button" disabled={bulkBusy} onClick={() => void runBulk("priority")} className="rounded-control bg-muted px-2 py-1 text-[11.5px] font-medium text-foreground hover:bg-border">Priority</button>
            <form className="flex items-center gap-1" onSubmit={(event) => { event.preventDefault(); void runBulk("tag"); }}>
              <input value={bulkTag} onChange={(event) => setBulkTag(event.target.value)} aria-label="Tag selected tickets" placeholder="Tag" className="h-7 w-16 rounded-control border border-border px-1.5 text-[11.5px] outline-none focus:border-focus" />
              <button type="submit" disabled={bulkBusy || !bulkTag.trim()} aria-label="Add tag to selected tickets" className="rounded-control bg-muted p-1.5 text-text-secondary hover:text-foreground"><Tag size={13} /></button>
            </form>
            <button type="button" onClick={() => setSelectedIds(new Set())} aria-label="Clear selection" className="rounded-control p-1.5 text-text-secondary hover:bg-muted hover:text-foreground"><X size={14} /></button>
            {bulkError ? <p role="alert" className="basis-full text-[11.5px] text-danger">{bulkError}</p> : null}
          </div>
        ) : null}
        {error ? <p role="alert" className="m-4 text-[13px] text-danger">{error}</p> : null}

        {loading && items.length === 0 ? (
          <div aria-hidden>
            {[0, 1, 2, 3, 4].map((row) => (
              <div key={row} className="space-y-1.5 border-b border-border px-4 py-3">
                <div className="h-3 w-28 rounded bg-muted" />
                <div className="h-3 w-48 rounded bg-muted" />
              </div>
            ))}
          </div>
        ) : visible.length === 0 ? (
          <p className="px-4 py-6 text-[13px] text-text-secondary">
            {items.length === 0 ? `No conversations in ${FOLDERS.find((f) => f.value === folder)?.label.toLowerCase()}.` : "No conversations match."}
          </p>
        ) : (
          <ul ref={listRef} aria-label="Conversations">
            {visible.map((item) => (
              <motion.li key={item.conversation_id} layout="position" transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}>
                <QueueRow
                  item={item}
                  selected={item.conversation_id === selectedConversationId}
                  checked={selectedIds.has(item.conversation_id)}
                  onSelect={() => onSelect(item.conversation_id)}
                  onToggle={() => toggleSelected(item.conversation_id)}
                />
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
