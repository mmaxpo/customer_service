import { customerServiceApi } from "@/domains/customer-service/api";

export const WorkflowLauncherService = {
  templates() {
    return customerServiceApi.workflowTemplates();
  },

  run(
    conversationId: string,
    templateId: string,
    message?: string,
  ) {
    return customerServiceApi.runWorkflowTemplateForConversation(
      conversationId,
      {
        template_id: templateId,
        message,
      },
    );
  },
};
