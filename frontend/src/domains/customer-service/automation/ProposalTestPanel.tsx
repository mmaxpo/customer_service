"use client";

import Link from "next/link";
import { CircleCheck, CircleX, Loader2, TriangleAlert } from "lucide-react";

import { cn } from "@/platform/utils";
import { Button } from "@/ui/primitives/button";

import { formatDay, formatTime } from "../inbox/case/format";
import { ToneChip } from "../inbox/case/parts";
import type { Proposal, TestCase, TestResults } from "./api";

// Publishing needs a test run with no failures, and at least one conversation
// that actually ran: a replay where the AI provider was down proves nothing.
export function testsAllowPublish(results: TestResults | null) {
  if (!results?.tested_at) return false;
  if (results.cases.some((c) => !c.passed && !c.provider_unavailable)) return false;
  return !results.cases.length || results.cases.some((c) => !c.provider_unavailable);
}

function Summary({ results }: { results: TestResults }) {
  if (!results.total) {
    return (
      <p className="rounded-container border border-border bg-muted p-3 text-[13px] text-text-secondary">
        This workflow has no past conversations to replay yet, so nothing was tested.
      </p>
    );
  }
  if (results.untested === results.total) {
    return (
      <p role="status" className="flex gap-1.5 rounded-container border border-warning/40 bg-warning/5 p-3 text-[13px] text-foreground">
        <TriangleAlert size={15} className="mt-0.5 shrink-0 text-warning" aria-hidden />
        None of the {results.total} conversations could run because the AI provider is unavailable. Test again once it&apos;s back to publish.
      </p>
    );
  }
  const failed = results.cases.filter((c) => !c.passed && !c.provider_unavailable).length;
  const ok = !failed;
  return (
    <div
      role="status"
      className={cn(
        "rounded-container border p-3",
        ok ? "border-commerce-accent/30 bg-commerce-accent/5" : "border-danger/30 bg-danger/5",
      )}
    >
      <p className={cn("flex items-center gap-1.5 text-[13.5px] font-semibold", ok ? "text-commerce-accent" : "text-danger")}>
        {ok ? <CircleCheck size={15} aria-hidden /> : <CircleX size={15} aria-hidden />}
        {results.passed} of {results.total} test conversations passed
      </p>
      <p className="mt-0.5 text-[12.5px] text-text-secondary">
        {results.changed} would now get a different answer
        {results.untested ? `. ${results.untested} couldn't run because the AI provider is unavailable` : ""}.
      </p>
    </div>
  );
}

function CaseCard({ testCase, baseVersion, draftVersion }: { testCase: TestCase; baseVersion: number; draftVersion: number }) {
  const status = testCase.provider_unavailable
    ? <ToneChip tone="neutral">Couldn&apos;t run</ToneChip>
    : !testCase.passed
      ? <ToneChip tone="failure">Failed</ToneChip>
      : testCase.changed
        ? <ToneChip tone="attention">Different</ToneChip>
        : <ToneChip tone="neutral">Same</ToneChip>;

  return (
    <li className="rounded-container border border-border p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11.5px] text-text-secondary">
          {formatDay(testCase.created_at)} at {formatTime(testCase.created_at)}
        </p>
        {status}
      </div>
      <p className="mt-1 text-[13px] font-medium text-foreground">&ldquo;{testCase.customer_message}&rdquo;</p>

      <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-text-secondary">Before · v{baseVersion}</p>
      <p className="mt-0.5 rounded bg-muted px-2 py-1.5 text-[12.5px] leading-5 text-text-secondary">
        {testCase.answer ?? "No answer was sent."}
      </p>

      <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-warning">After · v{draftVersion}</p>
      {testCase.provider_unavailable ? (
        <p className="mt-0.5 text-[12.5px] text-text-secondary">The AI provider is unavailable right now, so this couldn&apos;t be replayed.</p>
      ) : testCase.draft_answer ? (
        <p className={cn("mt-0.5 rounded border px-2 py-1.5 text-[12.5px] leading-5 text-foreground", testCase.changed ? "border-warning/40 bg-warning/5" : "border-border")}>
          {testCase.draft_answer}
        </p>
      ) : (
        <p className="mt-0.5 text-[12.5px] text-text-secondary">No reply would be sent.</p>
      )}
      {testCase.draft_error && !testCase.provider_unavailable ? (
        <p className="mt-1 text-[12px] text-danger">{testCase.draft_error}</p>
      ) : null}
      {testCase.fallback_used ? (
        <p className="mt-1 flex items-center gap-1 text-[12px] text-warning">
          <TriangleAlert size={12} aria-hidden /> The AI step fell back to its standby reply.
        </p>
      ) : null}
      {testCase.blocked_steps.length ? (
        <p className="mt-1 text-[12px] text-text-secondary">Held back in the test: {testCase.blocked_steps.join(", ")}.</p>
      ) : null}
      <Link href={`/app/workflows/runs/${testCase.run_id}`} className="mt-1.5 inline-block text-[12.5px] font-medium text-primary hover:underline">
        See the original run
      </Link>
    </li>
  );
}

export function ProposalTestPanel({
  proposal,
  testing,
  onTest,
}: {
  proposal: Proposal;
  testing: boolean;
  onTest: () => void;
}) {
  const results = proposal.test_results;
  const isDraft = proposal.status === "draft";

  return (
    <div className="space-y-3">
      <p className="text-[12.5px] leading-5 text-text-secondary">
        Replays recent conversations on this draft. Replies, order changes and approvals are held back, so customers see nothing.
      </p>
      {isDraft ? (
        <Button variant="secondary" size="sm" className="w-full" disabled={testing} onClick={onTest}>
          {testing ? <Loader2 size={14} className="mr-1.5 animate-spin" aria-hidden /> : null}
          {testing ? "Testing…" : results ? "Test again" : "Test on past conversations"}
        </Button>
      ) : null}

      {results ? (
        <>
          <Summary results={results} />
          <ul className="space-y-2">
            {results.cases.map((testCase) => (
              <CaseCard key={testCase.run_id} testCase={testCase} baseVersion={proposal.base_version} draftVersion={proposal.version} />
            ))}
          </ul>
        </>
      ) : proposal.recent_conversations.length ? (
        <p className="text-[12.5px] text-text-secondary">
          {proposal.recent_conversations.length} recent {proposal.recent_conversations.length === 1 ? "conversation" : "conversations"} will be replayed. Publishing needs a passing test.
        </p>
      ) : (
        <p className="text-[13px] text-text-secondary">This workflow hasn&apos;t handled a conversation yet.</p>
      )}
    </div>
  );
}
