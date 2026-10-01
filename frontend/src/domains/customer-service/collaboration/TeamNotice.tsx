"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AtSign, UserCheck, X } from "lucide-react";

import { apiJson } from "@/platform/api/client";

type Notification = {
  id: string;
  kind: string;
  entity_id: string | null;
  payload: { from?: string; excerpt?: string } | null;
};

const base = "/api/customer-service";
const REFRESH_MS = 30_000;

// Pops up when a teammate mentions you in a note or gives you a conversation.
export default function TeamNotice() {
  const [notices, setNotices] = useState<Notification[]>([]);

  useEffect(() => {
    const load = () =>
      apiJson<Notification[]>(`${base}/notifications?unread_only=true&limit=20`)
        .then((rows) => setNotices(rows.filter((row) => row.kind === "mention" || row.kind === "assigned").slice(0, 3)))
        .catch(() => {});
    void load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, []);

  if (!notices.length) return null;

  const dismiss = (id: string) => {
    setNotices((current) => current.filter((item) => item.id !== id));
    apiJson(`${base}/notifications/${id}/read`, { method: "POST" }).catch(() => {});
  };

  return (
    <div role="status" aria-live="polite" className="fixed inset-x-4 top-14 z-50 flex flex-col gap-2 sm:inset-x-auto sm:right-4 sm:w-80 lg:top-4">
      {notices.map((item) => {
        const mention = item.kind === "mention";
        const Icon = mention ? AtSign : UserCheck;
        return (
          <div key={item.id} className="flex items-start gap-2.5 rounded-container border border-primary/40 bg-surface p-3 shadow-lg">
            <Icon size={16} className="mt-0.5 shrink-0 text-primary" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-[13.5px] font-medium text-foreground">
                {item.payload?.from ?? "A teammate"} {mention ? "mentioned you in a note" : "assigned you a conversation"}
              </p>
              {mention && item.payload?.excerpt ? (
                <p className="mt-0.5 line-clamp-2 text-[13px] text-text-secondary">&ldquo;{item.payload.excerpt}&rdquo;</p>
              ) : null}
              {item.entity_id ? (
                <Link
                  href={`/app/inbox?conversation=${item.entity_id}`}
                  onClick={() => dismiss(item.id)}
                  className="mt-1.5 inline-block text-[13px] font-medium text-primary hover:underline"
                >
                  Open conversation
                </Link>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              aria-label="Dismiss"
              className="shrink-0 rounded-control p-1 text-text-secondary hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <X size={14} aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}
