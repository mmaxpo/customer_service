// Plain names for the topics the automatic conversation insight assigns.
export const TOPIC_LABELS: Record<string, string> = {
  tracking_request: "Order status",
  shipping_delay: "Shipping delay",
  refund_request: "Refund",
  cancellation_request: "Cancellation",
  return_exchange: "Return or exchange",
  damaged_item: "Damaged item",
  billing_issue: "Billing",
  general_support: "General question",
};

export function topicLabel(topic: string | null | undefined) {
  if (!topic) return null;
  return TOPIC_LABELS[topic] ?? topic.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
