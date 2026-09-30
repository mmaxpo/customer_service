import { customerServiceApi } from "@/domains/customer-service/api";

export const ReplyService = {
  compose(conversationId: string, customerMessage?: string | null) {
    return customerServiceApi.composeAIReply(
      conversationId,
      customerMessage ?? null,
      null,
    );
  },

  send(
    conversationId: string,
    body: string,
    meta: Record<string, unknown> | null,
    attachmentIds: string[] = [],
  ) {
    if (attachmentIds.length) {
      return customerServiceApi.enqueueOutboundMessage({
        conversation_id: conversationId,
        body,
        sender_type: "agent",
        idempotency_key: `inbox-${conversationId}-${crypto.randomUUID()}`,
        attachments: attachmentIds.map((attachment_id) => ({ attachment_id })),
        meta,
      });
    }
    return customerServiceApi.sendMessage(conversationId, {
      sender_type: "agent",
      body,
      meta,
    });
  },

  addInternalNote(
    conversationId: string,
    body: string,
  ) {
    return customerServiceApi.addInternalNote(
      conversationId,
      body,
      {
        source: "inbox",
      },
    );
  },
};
