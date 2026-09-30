export const Events = {

  ConversationChanged:
    "conversation.changed",

  ConversationDeleted:
    "conversation.deleted",

  MessageSent:
    "message.sent",

  MessageReceived:
    "message.received",

  RuntimeUpdated:
    "runtime.updated",

  WorkflowStarted:
    "workflow.started",

  WorkflowFinished:
    "workflow.finished",

  WorkflowFailed:
    "workflow.failed",

  SuggestedActionsChanged:
    "suggested-actions.changed",

  CommerceChanged:
    "commerce.changed",

} as const;
