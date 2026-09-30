"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { AIReplyComposeResponse, UploadedConversationAttachment } from "@/domains/customer-service/model";
import { customerServiceApi } from "@/domains/customer-service/api";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";

import { deriveCaseState, pickNextStep } from "../case/caseState";
import { useSuggestionDecision } from "../case/useSuggestionDecision";
import InboxRoot from "../components/InboxRoot";
import { useCommerceOrder } from "../features/commerce/hooks";
import {
  useCaseActivity,
  useCaseContext,
  useConversation,
  useCustomerSummary,
  useInbox,
} from "../hooks";
import { ReplyService } from "../services";
import { resolveOrderReference } from "../utils/orderRef";

export default function InboxController() {
  const publish = usePublish();
  const inbox = useInbox();
  const { setSelectedConversationId } = inbox;

  const clearSelection = useCallback(() => {
    setSelectedConversationId(null);
  }, [setSelectedConversationId]);

  const conversation = useConversation({
    conversationId: inbox.selectedConversationId,
    refreshInbox: inbox.refresh,
    clearSelection,
  });

  const current = conversation.current;
  const context = useCaseContext(inbox.selectedConversationId);
  const activity = useCaseActivity(inbox.selectedConversationId);
  const customerSummary = useCustomerSummary(current?.customer_id ?? null, inbox.selectedConversationId);
  const orderRef = useMemo(() => resolveOrderReference(context.data, current), [context.data, current]);
  const commerce = useCommerceOrder(orderRef?.ref ?? null);
  const decision = useSuggestionDecision(inbox.selectedConversationId);
  const { clearError } = decision;

  const [composerMode, setComposerMode] = useState<"reply" | "note">("reply");
  const [replyText, setReplyText] = useState("");
  const [internalNoteText, setInternalNoteText] = useState("");
  const [aiReply, setAiReply] = useState<AIReplyComposeResponse | null>(null);
  const [isComposing, setIsComposing] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [replyError, setReplyError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<UploadedConversationAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Reset the composer only when a different case opens.
  const currentId = current?.id;
  useEffect(() => {
    setComposerMode("reply");
    setReplyText("");
    setInternalNoteText("");
    setAiReply(null);
    setAttachments([]);
    setReplyError(null);
    clearError();
  }, [currentId, clearError]);

  const uploadAttachments = useCallback(async (files: File[]) => {
    if (!current || !files.length) return;
    setIsUploading(true);
    setReplyError(null);
    try {
      const uploaded = await Promise.all(files.map((file) => customerServiceApi.uploadConversationAttachment(current.id, file)));
      setAttachments((existing) => [...existing, ...uploaded]);
    } catch (err) {
      setReplyError(apiErrorMessage(err, "Could not upload attachment"));
    } finally {
      setIsUploading(false);
    }
  }, [current]);

  const notifyChanged = useCallback((conversationId: string) => {
    publish({ type: Events.ConversationChanged, payload: { conversationId } });
  }, [publish]);

  const composeReply = useCallback(async () => {
    if (!current) return;

    const latestCustomerMessage = [...current.messages]
      .reverse()
      .find((message) => message.sender_type === "customer");

    setComposerMode("reply");
    setIsComposing(true);
    setReplyError(null);

    try {
      const result = await ReplyService.compose(current.id, latestCustomerMessage?.body ?? null);
      setAiReply(result);
      setReplyText(result.body);
    } catch (err) {
      setReplyError(apiErrorMessage(err, "Tajeran couldn't draft a reply"));
    } finally {
      setIsComposing(false);
    }
  }, [current]);

  const sendReply = useCallback(async () => {
    if (!current || (!replyText.trim() && attachments.length === 0) || isUploading) return;

    setIsSending(true);
    setReplyError(null);

    try {
      await ReplyService.send(
        current.id,
        replyText.trim(),
        aiReply
          ? {
              ai_reply: {
                confidence: aiReply.confidence,
                reply_type: aiReply.reply_type,
                requires_review: aiReply.requires_review,
                source_summary: aiReply.source_summary,
              },
            }
          : null,
        attachments.map((attachment) => attachment.id),
      );

      setReplyText("");
      setAiReply(null);
      setAttachments([]);
      publish({ type: Events.MessageSent, payload: { conversationId: current.id } });
      notifyChanged(current.id);
    } catch (err) {
      setReplyError(apiErrorMessage(err, "Could not send the reply"));
    } finally {
      setIsSending(false);
    }
  }, [aiReply, attachments, current, isUploading, notifyChanged, publish, replyText]);

  const addInternalNote = useCallback(async () => {
    if (!current || !internalNoteText.trim()) return;

    setIsAddingNote(true);
    setReplyError(null);

    try {
      await ReplyService.addInternalNote(current.id, internalNoteText.trim());
      setInternalNoteText("");
      notifyChanged(current.id);
    } catch (err) {
      setReplyError(apiErrorMessage(err, "Could not add the note"));
    } finally {
      setIsAddingNote(false);
    }
  }, [current, internalNoteText, notifyChanged]);

  // A case is only shown once its detail belongs to the selected id.
  const selectedCase = current && current.id === inbox.selectedConversationId ? current : null;

  return (
    <InboxRoot
      queue={{
        items: inbox.items,
        folder: inbox.folder,
        setFolder: inbox.setFolder,
        loading: inbox.loading,
        error: inbox.error,
        refresh: inbox.refresh,
        selectedConversationId: inbox.selectedConversationId,
        select: setSelectedConversationId,
      }}
      caseFile={{
        conversation: selectedCase,
        loading: conversation.loading,
        error: conversation.error,
        deleting: conversation.deleting,
        deleteConversation: conversation.deleteConversation,
        context: context.data,
        activity: activity.data,
        activityLoading: activity.loading,
        activityError: activity.error,
        refreshActivity: () => void activity.refresh(),
        customerSummary: customerSummary.data,
        state: deriveCaseState(context.data, selectedCase),
        nextStep: pickNextStep(context.data, selectedCase),
        decision,
        orderRef,
        order: commerce.order,
        orderLoading: commerce.loading,
        orderError: commerce.error,
      }}
      composer={{
        composerMode,
        setComposerMode,
        replyText,
        internalNoteText,
        setReplyText,
        setInternalNoteText,
        aiReply,
        composeReply,
        sendReply,
        addInternalNote,
        isComposing,
        isSending,
        isAddingNote,
        error: replyError,
        attachments,
        uploadAttachments,
        removeAttachment: (attachmentId: string) => setAttachments((currentAttachments) => currentAttachments.filter((item) => item.id !== attachmentId)),
        isUploading,
      }}
    />
  );
}
