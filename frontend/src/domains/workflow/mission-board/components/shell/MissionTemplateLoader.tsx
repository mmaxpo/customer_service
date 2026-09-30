"use client";

import { useEffect } from "react";

import { customerServiceApi } from "@/domains/customer-service/api/customer-service";
import { useMissionBoardStore } from "@/domains/workflow/mission-board/store/useMissionBoardStore";

type Props = {
  templateId: string | null;
};

export function MissionTemplateLoader({ templateId }: Props) {
  const setTemplate = useMissionBoardStore((state) => state.setTemplate);

  useEffect(() => {
    let alive = true;

    async function loadTemplate() {
      if (!templateId) {
        setTemplate(null);
        return;
      }

      const templates = await customerServiceApi.workflowTemplates();
      if (!alive) return;

      const template = templates.find((item) => item.id === templateId) ?? null;
      setTemplate(template);
    }

    loadTemplate().catch(() => {
      if (alive) setTemplate(null);
    });

    return () => {
      alive = false;
    };
  }, [templateId, setTemplate]);

  return null;
}
