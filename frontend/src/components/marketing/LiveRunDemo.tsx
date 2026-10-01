"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import {
  BookOpen,
  Check,
  History,
  Loader2,
  type LucideIcon,
  MessageSquare,
  Pause,
  PenLine,
  Play,
  ShieldCheck,
  ShoppingBag,
  UserRound,
} from "lucide-react";

import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";

type Tone = "ai" | "store" | "approval" | "person";

type Step = {
  icon: LucideIcon;
  tone: Tone;
  label: string;
  result: string;
  // Shown instead of the spinner while the step waits on a person.
  waiting?: string;
  ms?: number;
};

type Scenario = {
  tab: string;
  customer: string;
  channel: string;
  message: string;
  steps: Step[];
  reply: { from: "tajeran" | "teammate"; text: string };
  outcome: string;
};

const SCENARIOS: Scenario[] = [
  {
    tab: "Where is my order?",
    customer: "Sarah Johnson",
    channel: "Chat on your store",
    message: "Hi, I ordered last week and nothing has arrived. Where is order #1004?",
    steps: [
      { icon: MessageSquare, tone: "ai", label: "Understand the question", result: "Order status" },
      { icon: ShoppingBag, tone: "store", label: "Find the order in Shopify", result: "#1004, paid, shipped Monday" },
      { icon: ShoppingBag, tone: "store", label: "Check the tracking", result: "In transit, due Thursday" },
      { icon: PenLine, tone: "ai", label: "Write and send the reply", result: "Sent in the same chat" },
    ],
    reply: {
      from: "tajeran",
      text: "Your order #1004 shipped on Monday and is in transit. The carrier expects to deliver it on Thursday. Here is your tracking link.",
    },
    outcome: "Resolved. Nobody on your team had to open it.",
  },
  {
    tab: "It arrived broken",
    customer: "Daniel Reyes",
    channel: "Email",
    message: "The mug from order #1003 arrived in pieces. Can I get my money back?",
    steps: [
      { icon: MessageSquare, tone: "ai", label: "Understand the question", result: "Damaged item, wants a refund" },
      { icon: ShoppingBag, tone: "store", label: "Find the order in Shopify", result: "#1003, delivered, $24.00" },
      { icon: BookOpen, tone: "ai", label: "Read your returns policy", result: "Damaged items are refunded in full" },
      {
        icon: ShieldCheck,
        tone: "approval",
        label: "Ask before refunding",
        result: "Approved by Maya",
        waiting: "Waiting for approval",
        ms: 2200,
      },
      { icon: ShoppingBag, tone: "store", label: "Refund in Shopify", result: "$24.00 refunded to the card" },
      { icon: PenLine, tone: "ai", label: "Write and send the reply", result: "Sent by email" },
    ],
    reply: {
      from: "tajeran",
      text: "I'm sorry the mug arrived broken. I've refunded the full $24.00 to your card. It should reach your account in a few days.",
    },
    outcome: "Resolved with one approval. The refund waited for a person.",
  },
  {
    tab: "Can I return this?",
    customer: "Priya Nair",
    channel: "Instagram",
    message: "Can I still send back the jacket I asked about yesterday? It was on sale.",
    steps: [
      { icon: MessageSquare, tone: "ai", label: "Understand the question", result: "Return or exchange" },
      { icon: History, tone: "ai", label: "Recall the conversation", result: "The jacket from order #0998" },
      { icon: BookOpen, tone: "ai", label: "Search your help articles", result: "Returns and exchanges" },
      { icon: PenLine, tone: "ai", label: "Write and send the reply", result: "Sent on Instagram" },
    ],
    reply: {
      from: "tajeran",
      text: "Yes. Sale items can be returned within 30 days, and your jacket from order #0998 is still inside that window. Want me to start the return?",
    },
    outcome: "Resolved from your own help articles.",
  },
  {
    tab: "I need a person",
    customer: "Tom Becker",
    channel: "Email",
    message: "I was charged twice and my bank has opened a dispute. I need to talk to someone.",
    steps: [
      { icon: MessageSquare, tone: "ai", label: "Understand the question", result: "Billing dispute" },
      { icon: ShieldCheck, tone: "approval", label: "Check what it is allowed to handle", result: "Disputes go to your team" },
      { icon: UserRound, tone: "person", label: "Hand over with a summary", result: "Assigned to Maya" },
    ],
    reply: {
      from: "teammate",
      text: "Hi Tom, Maya here. I can see both charges on your order. I'm reversing the duplicate now and will confirm once it's done.",
    },
    outcome: "Handed over. Tajeran stays quiet once a teammate has replied.",
  },
];

const TONE: Record<Tone, string> = {
  ai: "bg-[#7A4DFF]/10 text-[#7A4DFF]",
  store: "bg-[#00A37A]/10 text-[#00A37A]",
  approval: "bg-[#E8622A]/10 text-[#E8622A]",
  person: "bg-[#2F6BFF]/10 text-[#2F6BFF]",
};

const MESSAGE_MS = 1200;
const STEP_MS = 1100;
const HOLD_MS = 4500;

export function LiveRunDemo() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const [active, setActive] = useState(0);
  // 0 = message just arrived, 1..n = step n is running, n + 1 = finished.
  const [tick, setTick] = useState(0);
  const [paused, setPaused] = useState(false);

  const scenario = SCENARIOS[active];
  const last = scenario.steps.length + 1;
  // Without motion there is no playback: show each scenario already finished.
  const at = reduced ? last : tick;

  useEffect(() => {
    if (reduced || paused || !inView) return;
    const delay = tick === 0 ? MESSAGE_MS : tick === last ? HOLD_MS : (scenario.steps[tick - 1].ms ?? STEP_MS);
    const timer = window.setTimeout(() => {
      if (tick === last) {
        setActive((active + 1) % SCENARIOS.length);
        setTick(0);
      } else {
        setTick(tick + 1);
      }
    }, delay);
    return () => window.clearTimeout(timer);
  }, [active, tick, last, scenario, reduced, paused, inView]);

  const done = at === last;

  return (
    <div ref={ref}>
      <div className="mb-3 flex items-center gap-2">
        <div role="tablist" aria-label="Example conversations" className="flex flex-1 gap-1.5 overflow-x-auto pb-1">
          {SCENARIOS.map((item, index) => (
            <button
              key={item.tab}
              type="button"
              role="tab"
              aria-selected={index === active}
              onClick={() => {
                setActive(index);
                setTick(0);
              }}
              className={cn(
                "shrink-0 rounded-control border px-3 py-1.5 text-[13px] font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2",
                index === active
                  ? "border-primary bg-primary text-white"
                  : "border-border bg-surface text-text-secondary hover:text-foreground",
              )}
            >
              {item.tab}
            </button>
          ))}
        </div>
        {reduced ? null : (
          <button
            type="button"
            onClick={() => setPaused(!paused)}
            aria-label={paused ? "Play the demo" : "Pause the demo"}
            className="mb-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-control border border-border bg-surface text-text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2"
          >
            {paused ? <Play size={14} aria-hidden /> : <Pause size={14} aria-hidden />}
          </button>
        )}
      </div>

      <div className="grid overflow-hidden rounded-xl border border-border bg-surface shadow-elevated lg:grid-cols-[1fr_1.05fr]">
        {/* The conversation, as the customer sees it */}
        <div className="flex min-h-[300px] flex-col p-5 sm:p-6 lg:min-h-[440px]">
          <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
            <div className="min-w-0">
              <p className="truncate text-[14px] font-semibold text-foreground">{scenario.customer}</p>
              <p className="text-[12.5px] text-text-secondary">{scenario.channel}</p>
            </div>
            <span
              className={cn(
                "shrink-0 rounded-full px-2.5 py-1 text-[12px] font-medium",
                done ? "bg-shopify-50 text-shopify-700" : "bg-muted text-text-secondary",
              )}
            >
              {done ? (scenario.reply.from === "teammate" ? "With your team" : "Resolved") : "Open"}
            </span>
          </div>

          <div className="flex flex-1 flex-col gap-3 pt-4">
            <AnimatePresence mode="popLayout" initial={false}>
              <motion.div
                key={`message-${active}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="max-w-[88%] self-start rounded-xl rounded-bl-sm bg-muted px-3.5 py-2.5 text-[14px] leading-6 text-foreground"
              >
                {scenario.message}
              </motion.div>

              {at > 0 && !done ? (
                <motion.div
                  key={`working-${active}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-2 self-end text-[12.5px] text-text-secondary"
                >
                  <span className="flex gap-1" aria-hidden>
                    {[0, 1, 2].map((dot) => (
                      <motion.span
                        key={dot}
                        className="h-1.5 w-1.5 rounded-full bg-ai-accent"
                        animate={{ opacity: [0.25, 1, 0.25] }}
                        transition={{ duration: 1, repeat: Infinity, delay: dot * 0.18 }}
                      />
                    ))}
                  </span>
                  The agents are working on it
                </motion.div>
              ) : null}

              {done ? (
                <motion.div
                  key={`reply-${active}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="max-w-[88%] self-end"
                >
                  <p className="mb-1 flex items-center justify-end gap-1.5 text-[12px] text-text-secondary">
                    {scenario.reply.from === "tajeran" ? (
                      <>
                        <TajeranMark size={14} variant="actor" /> Tajeran
                      </>
                    ) : (
                      <>
                        <UserRound size={13} aria-hidden /> Maya, your team
                      </>
                    )}
                  </p>
                  <div
                    className={cn(
                      "rounded-xl rounded-br-sm px-3.5 py-2.5 text-[14px] leading-6",
                      scenario.reply.from === "tajeran" ? "bg-ai-50 text-ai-950" : "bg-tajeran-50 text-tajeran-950",
                    )}
                  >
                    {scenario.reply.text}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          <p
            className={cn(
              "mt-4 border-t border-border pt-3 text-[13px] font-medium text-foreground transition-opacity duration-300",
              done ? "opacity-100" : "opacity-0",
            )}
          >
            {scenario.outcome}
          </p>
        </div>

        {/* The workflow run behind it */}
        <div className="border-t border-border bg-background p-5 sm:p-6 lg:border-l lg:border-t-0">
          <p className="text-[13px] font-medium text-text-secondary">What the agents did</p>
          <ol className="mt-4 space-y-1">
            {scenario.steps.map((step, index) => {
              const number = index + 1;
              const running = at === number;
              const finished = at > number;
              const Icon = step.icon;
              return (
                <li
                  key={`${active}-${step.label}`}
                  className={cn(
                    "flex items-center gap-3 rounded-container px-2.5 py-2 transition-[opacity,background-color] duration-300",
                    running ? "bg-surface shadow-elevated" : "",
                    running || finished ? "opacity-100" : "opacity-35",
                  )}
                >
                  <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-control", TONE[step.tone])}>
                    <Icon size={15} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13.5px] font-medium text-foreground">{step.label}</span>
                    <span
                      className={cn(
                        "block truncate text-[12.5px] text-text-secondary transition-opacity duration-300",
                        finished ? "opacity-100" : running && step.waiting ? "opacity-100" : "opacity-0",
                      )}
                    >
                      {finished ? step.result : (step.waiting ?? step.result)}
                    </span>
                  </span>
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center" aria-hidden>
                    {finished ? (
                      <motion.span initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.2 }}>
                        <Check size={16} className="text-shopify-700" />
                      </motion.span>
                    ) : running && step.waiting ? (
                      <span className="h-2 w-2 animate-pulse rounded-full bg-warn-700" />
                    ) : running ? (
                      <Loader2 size={15} className="animate-spin text-text-secondary" />
                    ) : (
                      <span className="h-1.5 w-1.5 rounded-full bg-border" />
                    )}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>

      <p className="mt-3 text-[12.5px] text-text-secondary">
        Example conversations. In your workspace the steps use your store, your policies, and your approval rules.
      </p>
    </div>
  );
}
