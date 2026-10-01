"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "motion/react";
import { BookOpen, type LucideIcon, MessageSquare, PenLine, ShoppingBag, UserRound, Zap } from "lucide-react";

import { cn } from "@/platform/utils";

const EASE = [0.22, 1, 0.36, 1] as const;

type Agent = {
  name: string;
  icon: LucideIcon;
  // Each agent keeps one colour everywhere it appears.
  color: string;
  caption: string;
  finding: string;
};

export const AGENTS: Agent[] = [
  {
    name: "Triage agent",
    icon: MessageSquare,
    color: "#7A4DFF",
    caption: "Reads the message and works out what the customer needs.",
    finding: "Damaged item, wants a refund",
  },
  {
    name: "Order agent",
    icon: ShoppingBag,
    color: "#00A37A",
    caption: "Finds the order in Shopify and checks what was paid and delivered.",
    finding: "Order #1003, delivered, $24.00",
  },
  {
    name: "Policy agent",
    icon: BookOpen,
    color: "#2F6BFF",
    caption: "Reads your returns policy and decides what the customer is owed.",
    finding: "Damaged items are refunded in full",
  },
  {
    name: "Maya, your team",
    icon: UserRound,
    color: "#E8622A",
    caption: "A refund moves money, so the agents stop and ask a person first.",
    finding: "Refund of $24.00 approved",
  },
  {
    name: "Action agent",
    icon: Zap,
    color: "#E0349A",
    caption: "Issues the refund in Shopify the moment it is approved.",
    finding: "$24.00 refunded to the card",
  },
  {
    name: "Reply agent",
    icon: PenLine,
    color: "#5B3DF5",
    caption: "Writes the answer in your tone and sends it on the same channel.",
    finding: "Reply sent by email",
  },
];

const MESSAGE = "The mug from order #1003 arrived in pieces. Can I get my money back?";
const REPLY = "I'm sorry the mug arrived broken. I've refunded the full $24.00 to your card. It should reach your account in a few days.";

// Stage 0 is the message arriving; stage n is agent n taking its turn.
const STAGES = AGENTS.length + 1;

// One conversation passed from agent to agent. On screens with motion the
// scene is pinned and the scroll position drives every step.
export function AgentsScene() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [scrolled, setScrolled] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (value) => {
    setScrolled(Math.min(AGENTS.length, Math.floor(value * STAGES)));
  });
  // The line reaches agent n exactly when stage n begins.
  const fill = useTransform(scrollYProgress, [1 / STAGES, AGENTS.length / STAGES], [0, 1]);

  const stage = reduced ? AGENTS.length : scrolled;
  const current = stage > 0 ? AGENTS[stage - 1] : null;
  const done = stage === AGENTS.length;

  return (
    <div ref={ref} className={reduced ? "py-20" : "h-[440vh]"}>
      <div className={cn("flex flex-col justify-center", reduced ? "" : "sticky top-0 h-[100svh] overflow-hidden")}>
        <div className="mx-auto grid w-full max-w-6xl gap-6 px-5 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:gap-16">
          <div className="min-h-[132px] sm:min-h-[190px] lg:min-h-[260px]">
            <p
              className="text-[13px] font-semibold tabular-nums text-text-secondary transition-colors duration-300 sm:text-[14px]"
              style={current ? { color: current.color } : undefined}
            >
              {current ? `Step ${stage} of ${AGENTS.length}` : "A conversation, start to finish"}
            </p>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={stage}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3, ease: EASE }}
              >
                <h2 className="mt-2 font-[family-name:var(--font-display)] text-[30px] font-semibold leading-[1.08] tracking-tight text-foreground sm:text-[44px] lg:text-[56px]">
                  {current ? current.name : "A message arrives"}
                </h2>
                <p className="mt-3 max-w-md text-[15px] leading-6 text-text-secondary sm:text-[18px] sm:leading-8">
                  {current ? current.caption : "Keep scrolling. Each agent takes its turn and passes the conversation on."}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="relative isolate">
            {/* A soft wash of the working agent's colour behind the scene */}
            <motion.div
              aria-hidden
              className="pointer-events-none absolute -inset-x-6 -bottom-6 top-10 -z-10 rounded-[48px] blur-3xl"
              initial={false}
              animate={{ backgroundColor: current ? current.color : "#7A4DFF", opacity: done ? 0.1 : 0.2 }}
              transition={{ duration: 0.6 }}
            />
            {/* The team: the line fills as the conversation is passed along */}
            <ol className="relative flex justify-between" aria-label="Agents working on the conversation">
              <span aria-hidden className="absolute left-5 right-5 top-5 h-px bg-border" />
              <motion.span
                aria-hidden
                className="absolute left-5 right-5 top-[19px] h-[3px] origin-left rounded-full"
                style={{ scaleX: reduced ? 1 : fill, background: `linear-gradient(90deg, ${AGENTS.map((agent) => agent.color).join(", ")})` }}
              />
              {AGENTS.map((agent, index) => {
                const reached = stage > index;
                const active = stage === index + 1;
                const Icon = agent.icon;
                return (
                  <li key={agent.name} className="relative flex w-10 flex-col items-center">
                    {active && !reduced ? (
                      <motion.span
                        aria-hidden
                        className="absolute top-0 h-10 w-10 rounded-full"
                        style={{ backgroundColor: agent.color }}
                        animate={{ scale: [1, 1.7], opacity: [0.35, 0] }}
                        transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
                      />
                    ) : null}
                    <motion.span
                      animate={{ scale: active ? 1.15 : 1 }}
                      transition={{ duration: 0.3, ease: EASE }}
                      className={cn(
                        "relative flex h-10 w-10 items-center justify-center rounded-full border transition-colors duration-300",
                        reached ? "border-transparent text-white" : "border-border bg-surface text-text-secondary",
                      )}
                      style={reached ? { backgroundColor: agent.color } : undefined}
                    >
                      <Icon size={17} aria-hidden />
                    </motion.span>
                    <span
                      className={cn(
                        "mt-2 hidden whitespace-nowrap text-[11.5px] font-medium transition-colors duration-300 sm:block",
                        reached ? "text-foreground" : "text-text-secondary",
                      )}
                    >
                      {agent.name.split(",")[0].replace(" agent", "")}
                    </span>
                    <span className="sr-only sm:hidden">{agent.name}</span>
                  </li>
                );
              })}
            </ol>

            {/* The case file: every agent adds what it found */}
            <div className="mt-6 min-h-[390px] rounded-xl border border-border bg-surface p-4 shadow-elevated sm:mt-8 sm:min-h-[440px] sm:p-6">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[14px] font-semibold text-foreground">Daniel Reyes</p>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[12px] font-medium transition-colors duration-300",
                    done ? "bg-shopify-50 text-shopify-700" : stage === 4 ? "bg-warn-50 text-warn-700" : "bg-muted text-text-secondary",
                  )}
                >
                  {done ? "Resolved" : stage === 4 ? "Approved" : "Open"}
                </span>
              </div>
              <p className="mt-3 w-fit max-w-[92%] rounded-xl rounded-bl-sm bg-muted px-3.5 py-2.5 text-[13.5px] leading-5 text-foreground sm:text-[14px] sm:leading-6">
                {MESSAGE}
              </p>

              <ul className="mt-3 sm:mt-4">
                <AnimatePresence initial={false}>
                  {AGENTS.slice(0, stage).map((agent) => {
                    const Icon = agent.icon;
                    return (
                      <motion.li
                        key={agent.name}
                        initial={reduced ? false : { opacity: 0, x: 24 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 24, transition: { duration: 0.15 } }}
                        transition={{ duration: 0.4, ease: EASE }}
                        className="flex items-center gap-3 border-t border-border py-1.5 sm:py-2"
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white" style={{ backgroundColor: agent.color }}>
                          <Icon size={12} aria-hidden />
                        </span>
                        <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-foreground sm:text-[13.5px]">{agent.finding}</span>
                        <span className="hidden shrink-0 text-[12px] text-text-secondary sm:block">{agent.name}</span>
                      </motion.li>
                    );
                  })}
                </AnimatePresence>
              </ul>

              <AnimatePresence initial={false}>
                {done ? (
                  <motion.p
                    key="reply"
                    initial={reduced ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, transition: { duration: 0.15 } }}
                    transition={{ duration: 0.4, ease: EASE, delay: 0.15 }}
                    className="ml-auto mt-2 w-fit max-w-[92%] rounded-xl rounded-br-sm bg-tajeran-50 px-3.5 py-2.5 text-[13.5px] leading-5 text-tajeran-950 sm:text-[14px] sm:leading-6"
                  >
                    {REPLY}
                  </motion.p>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
