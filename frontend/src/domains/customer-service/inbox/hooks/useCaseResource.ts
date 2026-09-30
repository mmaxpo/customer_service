"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Events } from "@/platform/events";
import { eventBus } from "@/platform/events/EventBus";

const CASE_EVENTS = [
  Events.ConversationChanged,
  Events.SuggestedActionsChanged,
  Events.WorkflowFinished,
  Events.WorkflowFailed,
  Events.RuntimeUpdated,
] as const;

type Payload = { conversationId?: string } | undefined;

// Loads one resource keyed by id, keeps the previous value while refreshing,
// and ignores responses for an id that is no longer selected.
export function useCaseResource<T>(
  id: string | null,
  load: (id: string) => Promise<T>,
  errorLabel: string,
  refreshForConversation?: string | null,
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeId = useRef<string | null>(id);
  activeId.current = id;

  const fetchFor = useCallback(async (target: string) => {
    setLoading(true);
    try {
      const result = await load(target);
      if (activeId.current !== target) return;
      setData(result);
      setError(null);
    } catch (err) {
      if (activeId.current !== target) return;
      setError(apiErrorMessage(err, errorLabel));
    } finally {
      if (activeId.current === target) setLoading(false);
    }
  }, [load, errorLabel]);

  useEffect(() => {
    setData(null);
    setError(null);
    if (id) void fetchFor(id);
  }, [id, fetchFor]);

  const refresh = useCallback(async () => {
    if (id) await fetchFor(id);
  }, [id, fetchFor]);

  const scope = refreshForConversation === undefined ? id : refreshForConversation;

  useEffect(() => {
    if (!id) return;
    const onEvent = (payload: Payload) => {
      if (payload?.conversationId && scope && payload.conversationId !== scope) return;
      void fetchFor(id);
    };
    const unsubscribers = CASE_EVENTS.map((event) => eventBus.subscribe<Payload>(event, onEvent));
    return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
  }, [id, scope, fetchFor]);

  return { data, loading, error, refresh };
}
