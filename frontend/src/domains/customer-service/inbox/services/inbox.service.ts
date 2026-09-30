import { customerServiceApi } from "@/domains/customer-service/api";
import type { InboxFolder } from "@/domains/customer-service/model";

export const InboxService = {
  list(folder: InboxFolder = "inbox") {
    return customerServiceApi.inbox(folder);
  },

  getConversation(conversationId: string) {
    return customerServiceApi.conversation(conversationId);
  },

  deleteConversation(conversationId: string) {
    return customerServiceApi.deleteConversation(conversationId);
  },
};
