"use client";

import { useEffect, useState } from "react";

import type {
  WorkflowTemplate,
} from "@/domains/customer-service/model";

import { WorkflowLauncherService } from "../services";

export function useWorkflowLauncher() {
  const [templates, setTemplates] =
    useState<WorkflowTemplate[]>([]);

  const [loading, setLoading] =
    useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);

      try {
        const result =
          await WorkflowLauncherService.templates();

        if (!cancelled) {
          setTemplates(result);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    templates,
    loading,
    run: WorkflowLauncherService.run,
  };
}
