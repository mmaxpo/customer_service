"use client";

import { useCallback, useEffect, useState } from "react";

import { apiErrorMessage } from "@/platform/api/client";
import { Events, useEvent, usePublish } from "@/platform/events";
import type { WorkflowWait } from "@/domains/customer-service/model";
import { ApprovalsService } from "../services";

// Approvals cannot yet be linked to a conversation reliably (backend gap G1),
// so this hook only serves the workspace-wide list.
export function useApprovals() {
  const publish = usePublish();

  const [waits, setWaits] = useState<WorkflowWait[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutatingId, setMutatingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setWaits(await ApprovalsService.listWaiting());
      setError(null);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load approvals"));
    } finally {
      setLoading(false);
    }
  }, []);

  const decide = useCallback(async (waitId: string, approved: boolean) => {
    setMutatingId(waitId);

    try {
      const result = approved
        ? await ApprovalsService.approve(waitId)
        : await ApprovalsService.reject(waitId);

      publish({ type: Events.RuntimeUpdated, payload: { runId: result.workflow_run_id } });
      await refresh();
      return result;
    } finally {
      setMutatingId(null);
    }
  }, [publish, refresh]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEvent(Events.RuntimeUpdated, () => {
    void refresh();
  });

  return {
    waits,
    loading,
    error,
    mutatingId,
    refresh,
    approve: (waitId: string) => decide(waitId, true),
    reject: (waitId: string) => decide(waitId, false),
  };
}
