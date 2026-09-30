import { Inbox, MessageSquare, ShoppingBag } from "lucide-react";

export const channelDescriptions: Record<string, string> = {
  email: "Support email inbox for customer questions and replies.",
  chat: "Live chat / website widget conversations.",
  whatsapp: "WhatsApp customer conversations and delivery events.",
  facebook: "Facebook messages and social support.",
  instagram: "Instagram DMs for social commerce support.",
  shopify: "Shopify order context, customer context, and support actions.",
};

export function channelIcon(channel: string) {
  if (channel === "shopify") return ShoppingBag;
  if (channel === "email") return Inbox;
  return MessageSquare;
}

export function statusClass(status: string) {
  if (status.toLowerCase() === "active") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  return "border-slate-200 bg-slate-50 text-slate-600";
}
