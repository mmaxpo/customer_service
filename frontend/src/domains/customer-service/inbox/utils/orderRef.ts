import type {
  ConversationContext,
  ConversationDetail,
} from "@/domains/customer-service/model";

export type OrderRefSource = "insight" | "suggestion" | "message";

export type OrderReference = {
  ref: string;
  source: OrderRefSource;
};

export function extractOrderRef(text?: string | null) {
  if (!text) return null;

  const patterns = [
    /#\d{3,}/,
    /order\s*#?\s*([a-zA-Z0-9-]{3,})/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;

    return (match[1] ?? match[0])
      .replace(/^order\s*/i, "")
      .trim();
  }

  return null;
}

function firstString(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    const found = value.find((item) => typeof item === "string" && item.trim());
    return typeof found === "string" ? found.trim() : null;
  }
  return null;
}

// Backend-derived references win; the message regex is only a fallback.
export function resolveOrderReference(
  context: ConversationContext | null,
  conversation: ConversationDetail | null,
): OrderReference | null {
  const fromInsight = firstString(context?.latest_insight?.entities?.order_refs);
  if (fromInsight) return { ref: fromInsight, source: "insight" };

  const suggestions = [...(context?.suggested_actions ?? [])].sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  );
  for (const action of suggestions) {
    const ref = firstString(action.payload?.order_ref);
    if (ref) return { ref, source: "suggestion" };
  }

  if (conversation) {
    const candidates = [conversation.subject, ...conversation.messages.map((m) => m.body)];
    for (const candidate of candidates) {
      const ref = extractOrderRef(candidate);
      if (ref) return { ref, source: "message" };
    }
  }

  return null;
}
