"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { InboxFolder, InboxItem } from "@/domains/customer-service/model";
import { apiErrorMessage } from "@/platform/api/client";
import { Events, useEvent } from "@/platform/events";
import { InboxService } from "../services";

export function useInbox() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [folder, setFolder] = useState<InboxFolder>("inbox");
  const [selectedConversationId, setSelectedConversationId] =
    useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const folderRef = useRef(folder);
  folderRef.current = folder;

  const refresh = useCallback(async () => {
    const requested = folderRef.current;

    try {
      const conversations = await InboxService.list(requested);
      if (folderRef.current !== requested) return;

      setItems(conversations);
      setError(null);
      setSelectedConversationId((current) => {
        if (current) return current;
        return conversations[0]?.conversation_id ?? null;
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load the inbox"));
    } finally {
      if (folderRef.current === requested) setLoading(false);
    }
  }, []);

  // Deep link from other screens: /app/inbox?conversation=<id>
  useEffect(() => {
    const linked = new URLSearchParams(window.location.search).get("conversation");
    if (linked) setSelectedConversationId(linked);
  }, []);

  useEffect(() => {
    setLoading(true);
    void refresh();
  }, [folder, refresh]);

  const onConversationChanged = useCallback(() => {
    void refresh();
  }, [refresh]);

  useEvent(Events.ConversationChanged, onConversationChanged);

  return {
    items,
    folder,
    setFolder,
    loading,
    error,
    refresh,
    selectedConversationId,
    setSelectedConversationId,
  };
}
