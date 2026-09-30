import { Bot, CheckCircle2 } from "lucide-react";

import { Bubble, MessageCircle, Panel } from "./ChatbotUi";
import type { ChatWidgetSettings } from "@/domains/customer-service/api/customer-service";

type Props = {
  brandColor: string;
  draft: Partial<ChatWidgetSettings>;
};

export function StorefrontPreviewPanel({
  brandColor,
  draft,
}: Props) {
  return (
    <div>
      <Panel icon={Bot} title="Storefront preview">
        <div className="relative overflow-hidden rounded-[1.75rem] border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-emerald-50">
          <div className="border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-black text-slate-950">Demo Shopify Store</div>
                <div className="text-xs font-semibold text-slate-500">Live customer view</div>
              </div>
              <div className="hidden gap-3 text-xs font-bold text-slate-500 sm:flex">
                <span>Products</span>
                <span>Orders</span>
                <span>Support</span>
              </div>
            </div>
          </div>

          <div className="p-4">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="h-28 rounded-2xl bg-gradient-to-br from-slate-200 via-slate-100 to-emerald-50" />
              <div className="mt-4 flex items-end justify-between gap-3">
                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Order help</div>
                  <div className="mt-1 text-sm font-black text-slate-950">Premium product</div>
                  <div className="mt-1 text-xs text-slate-500">Need help? Chat is ready.</div>
                </div>
                <button className="rounded-2xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white">
                  Add to cart
                </button>
              </div>
            </div>
          </div>

          <div className="p-5">
            <div className="overflow-hidden rounded-[1.55rem] border border-slate-200 bg-white shadow-2xl">
              <div className="flex items-center gap-3 px-4 py-3 text-white" style={{ backgroundColor: brandColor }}>
                <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-white/20">
                  <Bot size={17} />
                </div>
                <div>
                  <div className="truncate text-sm font-black">{draft.title || "Chat with us"}</div>
                  <div className="truncate text-xs opacity-85">{draft.assistant_name || "Tajeran AI"}</div>
                </div>
              </div>

              <div className="space-y-3 bg-slate-50 p-4">
                <Bubble>{draft.welcome_message || "Hi! How can we help you today?"}</Bubble>
                <Bubble mine>Where is my order?</Bubble>
                <Bubble>I can help with that. Let me check your order status.</Bubble>
              </div>

              <div className="border-t border-slate-200 bg-white p-3">
                <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                  Type your message...
                  <div className="ml-auto flex h-8 w-8 items-center justify-center rounded-full text-white" style={{ backgroundColor: brandColor }}>
                    <MessageCircle size={15} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-800">
          <CheckCircle2 size={16} />
          Chat → Inbox → Agent reply → Widget is working.
        </div>
      </Panel>
    </div>
  );
}
