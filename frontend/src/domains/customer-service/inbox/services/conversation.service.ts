import { customerServiceApi } from "@/domains/customer-service/api";

export const ConversationService = {
  detail(conversationId: string) {
    return customerServiceApi.conversation(conversationId);
  },

  context(conversationId: string) {
    return customerServiceApi.conversationContext(conversationId);
  },

  activity(conversationId: string) {
    return customerServiceApi.automationActivity(conversationId);
  },

  customerSummary(customerId: string) {
    return customerServiceApi.customerSummary(customerId);
  },

  insights(conversationId: string) {
    return customerServiceApi.insights(conversationId);
  },

  analyze(conversationId: string) {
    return customerServiceApi.analyzeConversation(conversationId);
  },

  suggestedActions(conversationId: string) {
    return customerServiceApi.suggestedActions(conversationId);
  },

  generateSuggestedActions(conversationId: string) {
    return customerServiceApi.generateSuggestedActions(conversationId);
  },

  workflowExecutions(conversationId: string) {
    return customerServiceApi.workflowExecutions(conversationId);
  },

  tags(conversationId: string) {
    return customerServiceApi.tags(conversationId);
  },
};
