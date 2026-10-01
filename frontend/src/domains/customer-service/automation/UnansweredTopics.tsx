"use client";

import { useEffect, useState } from "react";

import { apiJson, jsonBody } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";

type Topic = { topic: string; count: number; examples: string[] };
type Topics = { days: number; topics: Topic[] };

const base = "/api/customer-service/studio/unanswered-topics";

/**
 * What customers asked this week that the automation handed to the team,
 * grouped by topic. Renders nothing when there is nothing to suggest.
 */
export function UnansweredTopics({ title }: { title: string }) {
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
            <div className="min-w-0 flex-1">
              <p className="text-[13.5px] text-foreground">
                Customers asked about <span className="font-semibold">{item.topic}</span> {item.count} times in the last {data.days} days,
                and the automation handed them to your team.
              </p>
              <p className="mt-0.5 truncate text-[12.5px] text-text-secondary">
                {item.examples.map((example) => `“${example}”`).join("  ·  ")}
              </p>
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={() => void dismiss(item.topic)}>Dismiss</Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
