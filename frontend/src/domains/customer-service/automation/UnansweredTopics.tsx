"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiJson, jsonBody } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

type Topic = { topic: string; count: number; examples: string[] };
type Topics = { days: number; topics: Topic[] };

const base = "/api/customer-service/studio/unanswered-topics";

/**
 * What customers asked this week that the automation handed to the team,
 * grouped by topic. Renders nothing when there is nothing to suggest.
 */
/** What to ask TCOS for when the owner wants a workflow for a topic. */
export const topicRequest = (item: { topic: string; examples: string[] }) =>
  `Answer customer questions about ${item.topic} from the help articles. Example questions: ${item.examples.join(" / ")}`;

export function UnansweredTopics({ title, onReview }: { title: string; onReview?: (request: string) => void }) {
  const [data, setData] = useState<Topics | null>(null);

  useEffect(() => {
    apiJson<Topics>(base).then(setData).catch(() => {});
  }, []);

  if (!data?.topics.length) return null;

  const dismiss = (topic: string) =>
    apiJson<Topics>(`${base}/dismiss`, { method: "POST", body: jsonBody({ topic }) }).then(setData).catch(() => {});

  return (
    <section className="rounded-container border border-border bg-surface px-4 py-3">
      <h2 className="text-[14px] font-semibold text-foreground">{title}</h2>
      <ul className="mt-1 divide-y divide-border">
        {data.topics.map((item) => (
          <li key={item.topic} className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 py-2.5">
            <div className="w-full min-w-0 sm:w-auto sm:flex-1">
              <p className="text-[13.5px] text-foreground">
                Customers asked about <span className="font-semibold">{item.topic}</span> {item.count} times in the last {data.days} days,
                and the automation handed them to your team.
              </p>
              <p className="mt-0.5 truncate text-[12.5px] text-text-secondary">
                {item.examples.map((example) => `“${example}”`).join("  ·  ")}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {onReview ? (
                <Button type="button" variant="secondary" size="sm" onClick={() => onReview(topicRequest(item))}>Review draft</Button>
              ) : (
                <Link
                  href={`/app/workflows?new=${encodeURIComponent(topicRequest(item))}`}
                  className="rounded-control px-2 py-1 text-[13px] font-medium text-primary hover:underline"
                >
                  Review draft
                </Link>
              )}
              <Button type="button" variant="ghost" size="sm" onClick={() => void dismiss(item.topic)}>Dismiss</Button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
