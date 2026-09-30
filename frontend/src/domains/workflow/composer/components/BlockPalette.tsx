"use client";

import {
  Bot,
  BookOpen,
  GitBranch,
  MessageCircle,
  Route,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Tag,
  Truck,
  UserPlus,
  XCircle,
} from "lucide-react";
import type { ComposerBlockKind } from "../types/composer";

type Props = {
  addBlock: (kind: ComposerBlockKind) => void;
  addUnderstandRequest: () => void;
  addSummarizeConversation: () => void;
  addReviewRefund: () => void;
  addAnalyzeSentiment: () => void;
  addCustomAgent: () => void;
  addOrderSupportAgent: () => void;
  addShopifyOrderCheck: () => void;
  addTrackingCheck: () => void;
  addRefundOrder: () => void;
  addCancelOrder: () => void;
  addTagConversation: () => void;
  addAssignAgent: () => void;
  addSearchDocuments: () => void;
  addSearchWeb: () => void;
};

type PaletteAction = {
  title: string;
  description: string;
  icon: any;
  onClick: () => void;
  tone: string;
};

function ActionButton({ action }: { action: PaletteAction }) {
  const Icon = action.icon;

  return (
    <button
      onClick={action.onClick}
      className="group flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white p-2.5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-tajeran-100 hover:bg-tajeran-50/40 hover:shadow-md"
    >
      <div className={["flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border", action.tone].join(" ")}>
        <Icon size={16} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-bold text-slate-950">{action.title}</div>
        <div className="mt-0.5 line-clamp-1 text-xs text-slate-500">{action.description}</div>
      </div>

      <div className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500 opacity-0 transition group-hover:opacity-100">
        Add
      </div>
    </button>
  );
}

export default function BlockPalette({
  addBlock,
  addUnderstandRequest,
  addSummarizeConversation,
  addReviewRefund,
  addAnalyzeSentiment,
  addCustomAgent,
  addOrderSupportAgent,
  addShopifyOrderCheck,
  addTrackingCheck,
  addRefundOrder,
  addCancelOrder,
  addTagConversation,
  addAssignAgent,
  addSearchDocuments,
  addSearchWeb,
}: Props) {
  const sections: Array<{
    title: string;
    description: string;
    actions: PaletteAction[];
  }> = [
    {
      title: "Start",
      description: "The beginning of the workflow",
      actions: [
        {
          title: "Customer Message",
          description: "Starts when a customer sends a message.",
          icon: MessageCircle,
          onClick: () => addBlock("customer_message_trigger"),
          tone: "border-tajeran-100 bg-tajeran-50 text-tajeran-700",
        },
      ],
    },
    {
      title: "Agents",
      description: "AI workers that understand, analyze, decide, and generate results.",
      actions: [
        {
          title: "Understand Request",
          description: "Identify customer intent and what they need.",
          icon: Bot,
          onClick: addUnderstandRequest,
          tone: "border-ai-100 bg-ai-50 text-ai-700",
        },
        {
          title: "Summarize Conversation",
          description: "Create a concise support summary.",
          icon: Sparkles,
          onClick: addSummarizeConversation,
          tone: "border-ai-100 bg-ai-50 text-ai-700",
        },
        {
          title: "Review Refund",
          description: "Analyze refund eligibility and risk.",
          icon: ShieldCheck,
          onClick: addReviewRefund,
          tone: "border-amber-100 bg-amber-50 text-amber-700",
        },
        {
          title: "Analyze Sentiment",
          description: "Detect mood, urgency, and escalation risk.",
          icon: Bot,
          onClick: addAnalyzeSentiment,
          tone: "border-purple-100 bg-purple-50 text-purple-700",
        },
        {
          title: "Order Support Agent",
          description: "Turn Shopify order data into a beautiful customer reply.",
          icon: Sparkles,
          onClick: addOrderSupportAgent,
          tone: "border-emerald-100 bg-emerald-50 text-emerald-700",
        },
        {
          title: "Custom Agent",
          description: "Create your own AI worker with custom instructions.",
          icon: Sparkles,
          onClick: addCustomAgent,
          tone: "border-tajeran-100 bg-tajeran-50 text-tajeran-700",
        },
      ],
    },
    {
      title: "Tools",
      description: "Actions that interact with Shopify, customer data, and systems.",
      actions: [
        {
          title: "Check Order",
          description: "Retrieve Shopify order details.",
          icon: Search,
          onClick: addShopifyOrderCheck,
          tone: "border-shopify-100 bg-shopify-50 text-shopify-700",
        },
        {
          title: "Check Shipping",
          description: "Retrieve shipment and tracking information.",
          icon: Truck,
          onClick: addTrackingCheck,
          tone: "border-shopify-100 bg-shopify-50 text-shopify-700",
        },
        {
          title: "Refund Order",
          description: "Prepare or execute a refund action.",
          icon: ShieldCheck,
          onClick: addRefundOrder,
          tone: "border-amber-100 bg-amber-50 text-amber-700",
        },
        {
          title: "Cancel Order",
          description: "Prepare or execute order cancellation.",
          icon: XCircle,
          onClick: addCancelOrder,
          tone: "border-red-100 bg-red-50 text-red-700",
        },
        {
          title: "Tag Conversation",
          description: "Apply intent, urgency, and support tags.",
          icon: Tag,
          onClick: addTagConversation,
          tone: "border-purple-100 bg-purple-50 text-purple-700",
        },
        {
          title: "Assign Agent",
          description: "Choose the right owner, queue, or team.",
          icon: UserPlus,
          onClick: addAssignAgent,
          tone: "border-tajeran-100 bg-tajeran-50 text-tajeran-700",
        },
      ],
    },
    {
      title: "Knowledge",
      description: "Information sources that agents can search and use.",
      actions: [
        {
          title: "Search Documents",
          description: "Search uploaded docs, policies, and knowledge base.",
          icon: BookOpen,
          onClick: addSearchDocuments,
          tone: "border-shopify-100 bg-shopify-50 text-shopify-700",
        },
        {
          title: "Search Web",
          description: "Search websites or external information sources.",
          icon: Search,
          onClick: addSearchWeb,
          tone: "border-ai-100 bg-ai-50 text-ai-700",
        },
      ],
    },
    {
      title: "Routing",
      description: "Control the workflow: branch, parallelize, approve, and merge.",
      actions: [
        {
          title: "Route Conversation",
          description: "Send work down paths using rules.",
          icon: Route,
          onClick: () => addBlock("business_router"),
          tone: "border-purple-100 bg-purple-50 text-purple-700",
        },
        {
          title: "Parallel Agents",
          description: "Run multiple agents and join results.",
          icon: GitBranch,
          onClick: () => addBlock("parallel_agents"),
          tone: "border-slate-200 bg-slate-50 text-slate-700",
        },
        {
          title: "Manager Approval",
          description: "Pause workflow until approval.",
          icon: ShieldCheck,
          onClick: () => addBlock("human_approval"),
          tone: "border-amber-100 bg-amber-50 text-amber-700",
        },
      ],
    },
    {
      title: "Response",
      description: "What the customer receives.",
      actions: [
        {
          title: "Reply to Customer",
          description: "Send the final customer-facing response.",
          icon: Send,
          onClick: () => addBlock("send_response"),
          tone: "border-emerald-100 bg-emerald-50 text-emerald-700",
        },
      ],
    },
  ];

  return (
    <aside className="w-80 shrink-0 overflow-y-auto border-r border-tajeran-100 bg-white p-4">
      <div className="rounded-[28px] bg-gradient-to-br from-tajeran-950 via-tajeran-700 to-ai-950 p-4 text-white shadow-xl shadow-tajeran-950/20">
        <div className="flex items-center gap-2 text-sm font-bold">
          <Sparkles size={16} />
          Workflow building blocks
        </div>
        <p className="mt-2 text-xs leading-5 text-tajeran-100">
          Build unlimited customer-service automations with triggers, agents, tools, knowledge, routing, and responses.
        </p>
      </div>

      <div className="mt-4 space-y-4">
        {sections.map((section) => (
          <section key={section.title}>
            <div className="mb-2 px-1">
              <div className="text-[11px] font-extrabold uppercase tracking-[0.18em] text-slate-400">
                {section.title}
              </div>
              <div className="mt-0.5 text-xs text-slate-500">{section.description}</div>
            </div>

            <div className="space-y-1.5">
              {section.actions.map((action) => (
                <ActionButton key={action.title} action={action} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </aside>
  );
}
