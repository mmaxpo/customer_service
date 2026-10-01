"use client";

import Link from "next/link";

import { useWaitingForPerson } from "@/domains/customer-service/live/useWaitingForPerson";

// These always go to a person, so no workflow is offered for them.
const HUMAN_ONLY_TOPICS = new Set(["cancellation_request", "refund_request", "damaged_item"]);

/** Offers to build a workflow when no workflow answered this conversation. */
export function WorkflowSuggestion({ conversationId, topic }: { conversationId: string; topic: string | null | undefined }) {
  const waiting = useWaitingForPerson()?.find((row) => row.conversation_id === conversationId);
  if (!waiting?.workflow_gap || HUMAN_ONLY_TOPICS.has(topic ?? "")) return null;

  const request = `Answer customer questions like this one from the help articles: "${waiting.last_customer_message}"`;
  return (
    <p className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-t border-border bg-surface px-4 py-2 text-[12.5px] text-text-secondary sm:px-5">
      {waiting.workflow_gap === "unanswered"
        ? "No workflow answered this. Build one for questions like it?"
        : "The workflow handed this to your team. Build one that answers questions like it?"}
      <Link href={`/app/workflows?new=${encodeURIComponent(request)}`} className="font-medium text-primary hover:underline">
        Review draft
      </Link>
    </p>
  );
}
