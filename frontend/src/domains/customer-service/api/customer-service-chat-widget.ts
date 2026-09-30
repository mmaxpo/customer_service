import { apiJson } from "@/platform/api/client";

import type {
  SeedWorkflowTemplatesResponse,
  UUID,
  WorkflowTemplate,
} from "@/domains/customer-service";

export type ChatWidgetSettings = {
  id: UUID;
  user_id: UUID;
  public_key: string;
  enabled: boolean;
  title: string;
  welcome_message: string;
  brand_color: string;
  position: string;
  assistant_name: string;
  auto_answer_enabled: boolean;
  auto_answer_confidence_threshold: number;
  human_handoff_enabled: boolean;
  human_handoff_message: string;
  workflow_template_id: UUID | null;
  meta: Record<string, unknown> | null;
};

export type ChatWidgetSettingsUpdate = Partial<{
  enabled: boolean;
  title: string;
  welcome_message: string;
  brand_color: string;
  position: string;
  assistant_name: string;
  auto_answer_enabled: boolean;
  auto_answer_confidence_threshold: number;
  human_handoff_enabled: boolean;
  human_handoff_message: string;
  workflow_template_id: UUID | null;
  meta: Record<string, unknown> | null;
}>;

export async function getChatWidgetSettings() {
  return apiJson<ChatWidgetSettings>("/api/customer-service/chat/widget/settings");
}

export async function updateChatWidgetSettings(payload: ChatWidgetSettingsUpdate) {
  return apiJson<ChatWidgetSettings>("/api/customer-service/chat/widget/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function listWorkflowTemplates() {
  return apiJson<WorkflowTemplate[]>("/api/customer-service/workflow-templates");
}

export async function seedShopifyWorkflowTemplates() {
  return apiJson<SeedWorkflowTemplatesResponse>(
    "/api/customer-service/workflow-templates/seed-shopify",
    { method: "POST" },
  );
}
