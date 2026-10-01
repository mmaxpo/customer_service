"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { UserRound, X } from "lucide-react";

import type { WaitingConversation } from "./api";
import { useWaitingForPerson } from "./useWaitingForPerson";

// Pops up when a conversation newly needs a person, on any screen of the app.
export default function HandoffNotice() {
  const waiting = useWaitingForPerson();
  const seen = useRef<Set<string> | null>(null);
  const [notices, setNotices] = useState<WaitingConversation[]>([]);

  useEffect(() => {
    if (!waiting) return;
    const ids = new Set<string>(waiting.map((item) => item.conversation_id));
    // Conversations already waiting when the app opened are not news.
    const fresh = seen.current ? waiting.filter((item) => !seen.current!.has(item.conversation_id)) : [];
    seen.current = ids;
    setNotices((current) => [...current.filter((item) => ids.has(item.conversation_id)), ...fresh].slice(-3));
  }, [waiting]);

  if (!notices.length) return null;

  const dismiss = (id: string) => setNotices((current) => current.filter((item) => item.conversation_id !== id));

  return (
    <div role="status" aria-live="polite" className="fixed inset-x-4 bottom-20 z-50 flex flex-col gap-2 sm:inset-x-auto sm:right-4 sm:w-80 lg:bottom-4">
      {notices.map((item) => (
        <div key={item.conversation_id} className="flex items-start gap-2.5 rounded-container border border-warning/50 bg-surface p-3 shadow-lg">
          <UserRound size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-[13.5px] font-medium text-foreground">{item.customer_name ?? "A customer"} needs a person</p>
            <p className="mt-0.5 truncate text-[13px] text-text-secondary">&ldquo;{item.last_customer_message}&rdquo;</p>
            <Link
              href={`/app/inbox?conversation=${item.conversation_id}`}
              onClick={() => dismiss(item.conversation_id)}
              className="mt-1.5 inline-block text-[13px] font-medium text-primary hover:underline"
            >
              Open conversation
            </Link>
          </div>
          <button
            type="button"
            onClick={() => dismiss(item.conversation_id)}
            aria-label="Dismiss"
            className="shrink-0 rounded-control p-1 text-text-secondary hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            <X size={14} aria-hidden />
          </button>
        </div>
      ))}
    </div>
  );
}
