"use client";

import { useState } from "react";
import { MotionConfig } from "motion/react";

import type {
  AIReplyComposeResponse,
  AutomationActivity,
  ConversationContext,
  ConversationDetail,
  CustomerSummary,
  InboxFolder,
  InboxItem,
  ShopifyOrder,
} from "@/domains/customer-service/model";
import { cn } from "@/platform/utils";
import { Sheet } from "@/ui/overlay/Sheet";

import { CaseHeader } from "../case/CaseHeader";
import { CaseTimeline } from "../case/CaseTimeline";
import { WorkflowSuggestion } from "../case/WorkflowSuggestion";
import { CommercePanel } from "../case/CommercePanel";
import { NextStep } from "../case/NextStep";
import type { CaseState, NextStep as Step } from "../case/caseState";
import type { useSuggestionDecision } from "../case/useSuggestionDecision";
import type { OrderReference } from "../utils/orderRef";
import { InboxQueue } from "./list/InboxQueue";
import { ReplyComposer } from "./reply/ReplyComposer";

export type InboxRootProps = {
  queue: {
    items: InboxItem[];
    folder: InboxFolder;
    setFolder: (folder: InboxFolder) => void;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    selectedConversationId: string | null;
    select: (conversationId: string) => void;
  };
  caseFile: {
    conversation: ConversationDetail | null;
    loading: boolean;
    error: string | null;
    deleting: boolean;
    deleteConversation: () => void;
    context: ConversationContext | null;
    activity: AutomationActivity | null;
    activityLoading: boolean;
    activityError: string | null;
    refreshActivity: () => void;
    customerSummary: CustomerSummary | null;
    state: CaseState | null;
    nextStep: Step | null;
    decision: ReturnType<typeof useSuggestionDecision>;
    orderRef: OrderReference | null;
    order: ShopifyOrder | null;
    orderLoading: boolean;
    orderError: string | null;
  };
  composer: {
    composerMode: "reply" | "note";
    setComposerMode: (mode: "reply" | "note") => void;
    replyText: string;
    internalNoteText: string;
    setReplyText: (value: string) => void;
    setInternalNoteText: (value: string) => void;
    aiReply: AIReplyComposeResponse | null;
    composeReply: () => void;
    sendReply: () => void;
    addInternalNote: () => void;
    isComposing: boolean;
    isSending: boolean;
    isAddingNote: boolean;
    error: string | null;
    attachments: { id: string; filename: string; content_type: string; size_bytes: number; scan_status: string }[];
    uploadAttachments: (files: File[]) => Promise<void>;
    removeAttachment: (attachmentId: string) => void;
    isUploading: boolean;
  };
};

export default function InboxRoot({ queue, caseFile, composer }: InboxRootProps) {
  const [mobilePane, setMobilePane] = useState<"list" | "case">("list");
  const [contextOpen, setContextOpen] = useState(false);
  const { conversation } = caseFile;

  const commerce = conversation ? (
    <CommercePanel
      conversation={conversation}
      context={caseFile.context}
      customerSummary={caseFile.customerSummary}
      orderRef={caseFile.orderRef}
      order={caseFile.order}
      orderLoading={caseFile.orderLoading}
      orderError={caseFile.orderError}
      decision={caseFile.decision}
    />
  ) : null;

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-full min-h-0 bg-surface">
        <aside
          aria-label="Conversation queue"
          className={cn(
            "min-h-0 w-full shrink-0 border-r border-border bg-background lg:block lg:w-[300px] xl:w-[320px]",
            mobilePane === "case" ? "hidden" : "block",
          )}
        >
          <InboxQueue
            items={queue.items}
            folder={queue.folder}
            onFolderChange={queue.setFolder}
            selectedConversationId={queue.selectedConversationId}
            onSelect={(conversationId) => {
              queue.select(conversationId);
              setMobilePane("case");
            }}
            loading={queue.loading}
            error={queue.error}
            refresh={queue.refresh}
          />
        </aside>

        <section
          aria-label="Case"
          className={cn("min-h-0 min-w-0 flex-1 flex-col", mobilePane === "list" ? "hidden lg:flex" : "flex")}
        >
          {caseFile.loading && !conversation ? (
            <div className="flex flex-1 items-center justify-center text-[13px] text-text-secondary">Loading case…</div>
          ) : !conversation ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-1 px-6 text-center">
              <p className="text-[14px] font-medium text-foreground">
                {caseFile.error ? "This case couldn't be loaded" : "No case selected"}
              </p>
              <p className="text-[13px] text-text-secondary">
                {caseFile.error ?? "Choose a conversation from the queue to see its full story."}
              </p>
            </div>
          ) : (
            <>
              <CaseHeader
                conversation={conversation}
                context={caseFile.context}
                state={caseFile.state}
                onBack={() => setMobilePane("list")}
                onOpenContext={() => setContextOpen(true)}
                onDelete={caseFile.deleteConversation}
                deleting={caseFile.deleting}
              />
              <CaseTimeline
                conversationId={conversation.id}
                customerName={conversation.customer?.name ?? conversation.customer?.email ?? null}
                items={caseFile.activity?.items ?? null}
                loading={caseFile.activityLoading}
                error={caseFile.activityError}
                onRetry={caseFile.refreshActivity}
                onQuote={(mode, text) => {
                  const quote = `> ${text.replace(/\s+/g, " ").trim().slice(0, 200)}\n`;
                  composer.setComposerMode(mode);
                  if (mode === "reply") composer.setReplyText(quote + composer.replyText.replace(/^(> .*\n)+/, ""));
                  else composer.setInternalNoteText(quote + composer.internalNoteText.replace(/^(> .*\n)+/, ""));
                  // Put the cursor after the quote so the person can type straight away.
                  window.setTimeout(() => {
                    const box = document.querySelector<HTMLTextAreaElement>('section[aria-label="Case"] textarea');
                    box?.focus();
                    box?.setSelectionRange(box.value.length, box.value.length);
                  }, 50);
                }}
              />
              <WorkflowSuggestion
                conversationId={conversation.id}
                topic={queue.items.find((item) => item.conversation_id === conversation.id)?.topic}
              />
              <NextStep step={caseFile.nextStep} conversationId={conversation.id} decision={caseFile.decision} />
              {composer.error ? (
                <p role="alert" className="shrink-0 border-t border-border bg-surface px-4 pt-2 text-[12.5px] text-danger sm:px-5">
                  {composer.error}
                </p>
              ) : null}
              <ReplyComposer {...composer} />
            </>
          )}
        </section>

        <aside
          aria-label="Customer and order"
          className="hidden min-h-0 w-[320px] shrink-0 overflow-y-auto border-l border-border bg-background xl:block"
        >
          {commerce}
        </aside>

        <Sheet open={contextOpen} onOpenChange={setContextOpen} title="Customer & order">
          {commerce}
        </Sheet>
      </div>
    </MotionConfig>
  );
}
