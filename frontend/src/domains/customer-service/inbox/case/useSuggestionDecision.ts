"use client";

import { useCallback, useState } from "react";

import { customerServiceApi } from "@/domains/customer-service/api";
import type { SuggestedAction } from "@/domains/customer-service/model";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, usePublish } from "@/platform/events";

import { lower } from "./format";

export function useSuggestionDecision(conversationId: string | null) {
  const publish = usePublish();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const changed = useCallback(() => {
    if (!conversationId) return;
    publish({ type: Events.SuggestedActionsChanged, payload: { conversationId } });
    publish({ type: Events.ConversationChanged, payload: { conversationId } });
  }, [conversationId, publish]);

  const perform = useCallback(async (action: SuggestedAction, work: () => Promise<unknown>) => {
    setBusyId(action.id);
    setError(null);
    try {
      await work();
      changed();
      return true;
    } catch (err) {
      setError(apiErrorMessage(err, "That didn't work. Try again."));
      changed();
      return false;
    } finally {
      setBusyId(null);
    }
  }, [changed]);

  // The backend only executes accepted suggestions.
  const execute = useCallback((action: SuggestedAction, payloadOverride: Record<string, unknown> = {}) => perform(action, async () => {
    if (lower(action.status) === "suggested") {
      await customerServiceApi.acceptSuggestedAction(action.id);
    }
    const payload: Record<string, unknown> = { ...payloadOverride };
    if (action.action_type === "reply" && typeof action.payload?.body === "string") payload.body = action.payload.body;
    if (action.action_type === "assign" && typeof action.payload?.assigned_to === "string") payload.assigned_to = action.payload.assigned_to;
    await customerServiceApi.executeSuggestedAction(action.id, payload);
  }), [perform]);

  const accept = useCallback((action: SuggestedAction) => perform(action, () =>
    customerServiceApi.acceptSuggestedAction(action.id),
  ), [perform]);

  const dismiss = useCallback((action: SuggestedAction) => perform(action, () =>
    customerServiceApi.rejectSuggestedAction(action.id),
  ), [perform]);

  const clearError = useCallback(() => setError(null), []);

  return { busyId, error, clearError, execute, accept, dismiss };
}
