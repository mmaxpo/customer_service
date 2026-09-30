"use client";

import { useEffect } from "react";

import { Events, eventBus } from "@/platform/events";

type WorkflowStreamEvent = {
  type?: string;
  event?: string;
  payload?: unknown;
  data?: unknown;
};

type Options = {
  conversationId?: string | null;
};

function parseMessage(raw: string): WorkflowStreamEvent | null {
  try {
    return JSON.parse(raw) as WorkflowStreamEvent;
  } catch {
    return null;
  }
}

export function useWorkflowRunStream(
  runId: string | null | undefined,
  options: Options = {},
) {
  useEffect(() => {
    if (!runId) return;

    const source = new EventSource(`/api/workflows/runs/${runId}/stream`);
    let disconnected = false;

    source.onmessage = (message) => {
      const parsed = parseMessage(message.data);
      const payload = {
        runId,
        workflowRunId: runId,
        conversationId: options.conversationId ?? undefined,
        raw: parsed ?? message.data,
      };

      eventBus.publish({
        type: Events.RuntimeUpdated,
        payload,
      });

      const eventType = parsed?.type ?? parsed?.event;

      if (eventType?.includes("finished") || eventType?.includes("completed")) {
        eventBus.publish({
          type: Events.WorkflowFinished,
          payload,
        });
      }

      if (eventType?.includes("failed") || eventType?.includes("error")) {
        eventBus.publish({
          type: Events.WorkflowFailed,
          payload,
        });
      }
    };

    source.onerror = () => {
      // EventSource reconnects automatically after an error. A terminal
      // workflow stream is intentionally closed by the backend, so allowing
      // the browser to reconnect creates a tight loop of requests, which can
      // trip the agent rate limiter and flood the Inbox with false errors.
      if (disconnected) return;
      disconnected = true;
      source.close();

      eventBus.publish({
        type: Events.RuntimeUpdated,
        payload: {
          runId,
          workflowRunId: runId,
          conversationId: options.conversationId ?? undefined,
          error: "workflow-run-stream-disconnected",
        },
      });
    };

    return () => {
      disconnected = true;
      source.close();
    };
  }, [runId, options.conversationId]);
}
