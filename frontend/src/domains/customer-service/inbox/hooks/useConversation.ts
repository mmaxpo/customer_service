"use client";

import { useCallback, useEffect, useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Events, useEvent } from "@/platform/events";
import type { ConversationDetail } from "@/domains/customer-service/model";
import { InboxService } from "../services";

type UseConversationOptions = {
  conversationId: string | null;
  refreshInbox: () => Promise<void>;
  clearSelection: () => void;
};

export function useConversation({
  conversationId,
  refreshInbox,
  clearSelection,
}: UseConversationOptions) {
  const [current, setCurrent] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (targetConversationId: string, silent = false) => {
      if (!silent) setLoading(true);
      setError(null);

      try {
        const conversation = await InboxService.getConversation(targetConversationId);
        setCurrent(conversation);
      } catch (err) {
        setError(apiErrorMessage(err, "Could not load the conversation"));
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [],
  );

  const refresh = useCallback(async () => {
    if (!conversationId) return;
    await load(conversationId, true);
  }, [conversationId, load]);

  const deleteConversation = useCallback(async () => {
    if (!current) return;

    setDeleting(true);
    setError(null);

    try {
      await InboxService.deleteConversation(current.id);
      setCurrent(null);
      clearSelection();
      await refreshInbox();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not delete the conversation"));
    } finally {
      setDeleting(false);
    }
  }, [clearSelection, current, refreshInbox]);

  useEffect(() => {
    if (!conversationId) {
      setCurrent(null);
      return;
    }

    void load(conversationId);
  }, [conversationId, load]);

  useEvent<{ conversationId?: string }>(
    Events.ConversationChanged,
    (payload) => {
      if (!conversationId) return;
      if (payload?.conversationId && payload.conversationId !== conversationId) return;

      void refresh();
      void refreshInbox();
    },
  );

  return {
    current,
    loading,
    deleting,
    error,
    refresh,
    deleteConversation,
  };
}
