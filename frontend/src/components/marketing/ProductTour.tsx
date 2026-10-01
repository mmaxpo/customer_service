"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { animate, AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import { Check, ShieldCheck } from "lucide-react";

import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";

const EASE = [0.22, 1, 0.36, 1] as const;
const frame = "w-full max-w-md rounded-xl border border-border bg-surface p-5 shadow-elevated sm:p-6";

// Advances 0 → last on a timer once the visual is on screen. Without motion
// it jumps straight to the finished state.
function useStages(delays: number[]) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!inView || reduced || stage >= delays.length) return;
    const timer = window.setTimeout(() => setStage(stage + 1), delays[stage]);
    return () => window.clearTimeout(timer);
  }, [inView, reduced, stage, delays]);

  return { ref, inView, stage: reduced ? delays.length : stage };
}

const APPROVAL_DELAYS = [1800];

function ApprovalVisual() {
  const { ref, stage } = useStages(APPROVAL_DELAYS);
  const approved = stage === 1;
  return (
    <div ref={ref} className={frame}>
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-[13px] font-medium text-text-secondary">
          <ShieldCheck size={15} className="text-warning" aria-hidden /> Approvals
        </span>
        <span
          className={cn(
            "rounded-full px-2.5 py-1 text-[12px] font-medium transition-colors duration-300",
            approved ? "bg-shopify-50 text-shopify-700" : "bg-warn-50 text-warn-700",
          )}
        >
          {approved ? "Approved" : "Waiting for you"}
        </span>
      </div>
      <p className="mt-4 text-[18px] font-semibold text-foreground">Refund $24.00 for order #1003</p>
      <dl className="mt-4 divide-y divide-border border-y border-border text-[13.5px]">
        {[
          ["Customer", "Daniel Reyes"],
          ["Reason", "Mug arrived broken"],
          ["Policy used", "Damaged items are refunded in full"],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 py-2.5">
            <dt className="text-text-secondary">{label}</dt>
            <dd className="text-right font-medium text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-5 flex h-10 items-center">
        <AnimatePresence mode="wait" initial={false}>
          {approved ? (
            <motion.p
              key="done"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex items-center gap-2 text-[13.5px] font-medium text-shopify-700"
            >
              <Check size={16} aria-hidden /> Refunded in Shopify and the customer has been told
            </motion.p>
          ) : (
            <motion.div key="actions" exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex w-full gap-2">
              <span className="flex h-10 flex-1 items-center justify-center rounded-control border border-border text-[13.5px] font-semibold text-foreground">
                Decline
              </span>
              <motion.span
                animate={{ scale: [1, 1, 0.95, 1] }}
                transition={{ duration: 1.8, times: [0, 0.8, 0.9, 1] }}
                className="flex h-10 flex-1 items-center justify-center rounded-control bg-primary text-[13.5px] font-semibold text-primary-foreground"
              >
                Approve
              </motion.span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function Counter({ to, play }: { to: number; play: boolean }) {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!play || reduced) return;
    const controls = animate(0, to, { duration: 1.1, ease: EASE, onUpdate: (next) => setValue(Math.round(next)) });
    return () => controls.stop();
  }, [play, reduced, to]);
  return <>{reduced ? to : value}</>;
}

const NO_DELAYS: number[] = [];
const REPLY_MINUTES = [9, 7, 6, 4, 3, 2, 2];

function SuperviseVisual() {
  const { ref, inView } = useStages(NO_DELAYS);
  const reduced = useReducedMotion();
  return (
    <div ref={ref} className={frame}>
      <p className="text-[13px] font-medium text-text-secondary">Live</p>
      <dl className="mt-3 grid grid-cols-3 divide-x divide-border rounded-container border border-border">
        {[
          ["Waiting for a person", 2],
          ["Waiting for approval", 1],
          ["Automations running", 14],
        ].map(([label, value]) => (
          <div key={label} className="px-3 py-3">
            <dt className="text-[12px] leading-4 text-text-secondary">{label}</dt>
            <dd className="mt-1 text-[22px] font-semibold tabular-nums text-foreground">
              <Counter to={value as number} play={inView} />
            </dd>
          </div>
        ))}
      </dl>

      <p className="mt-6 text-[13px] font-medium text-text-secondary">Desk: time to first reply, last 7 days</p>
      <div className="mt-3 flex h-28 items-end gap-2 border-b border-border" aria-hidden>
        {REPLY_MINUTES.map((minutes, index) => (
          <motion.span
            key={index}
            className="flex-1 origin-bottom rounded-t-[3px] bg-primary"
            style={{ height: `${(minutes / 9) * 100}%`, opacity: 0.45 + (index / REPLY_MINUTES.length) * 0.55 }}
            initial={reduced ? false : { scaleY: 0 }}
            animate={inView || reduced ? { scaleY: 1 } : undefined}
            transition={{ duration: 0.7, ease: EASE, delay: 0.2 + index * 0.07 }}
          />
        ))}
      </div>
      <p className="mt-3 text-[12.5px] text-text-secondary">Example figures.</p>
    </div>
  );
}

const CHANGE = "For damaged items, offer a replacement before a refund.";
const IMPROVE_DELAYS = [2400, 1500, 1500];

function ImproveVisual() {
  const { ref, inView, stage } = useStages(IMPROVE_DELAYS);
  const reduced = useReducedMotion();
  const [typed, setTyped] = useState(0);

  useEffect(() => {
    if (!inView || reduced) return;
    const controls = animate(0, CHANGE.length, { duration: 2, ease: "linear", onUpdate: (next) => setTyped(Math.round(next)) });
    return () => controls.stop();
  }, [inView, reduced]);

  const steps: { label: string; added?: boolean }[] = [
    { label: "Understand the question" },
    { label: "Read your returns policy" },
    ...(stage >= 1 ? [{ label: "Offer a replacement first", added: true }] : []),
    { label: "Ask before refunding" },
  ];

  return (
    <div ref={ref} className={frame}>
      <p className="text-[13px] font-medium text-text-secondary">Describe the change</p>
      <p className="mt-2 min-h-[68px] rounded-container border border-border bg-background px-3 py-2.5 text-[14px] leading-6 text-foreground">
        {reduced ? CHANGE : CHANGE.slice(0, typed)}
        {!reduced && stage === 0 ? <span className="ml-0.5 inline-block h-4 w-px animate-pulse bg-foreground align-middle" aria-hidden /> : null}
      </p>

      <p className="mt-5 flex items-center gap-2 text-[13px] font-medium text-text-secondary">
        <TajeranMark size={14} variant="actor" /> Damaged item workflow
      </p>
      <ol className="mt-2 space-y-1.5">
        <AnimatePresence initial={false}>
          {steps.map((step) => (
            <motion.li
              key={step.label}
              layout={!reduced}
              initial={step.added ? { opacity: 0, x: -12 } : false}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.45, ease: EASE }}
              className={cn(
                "flex items-center justify-between rounded-container border px-3 py-2 text-[13.5px] font-medium",
                step.added ? "border-ai-100 bg-ai-50 text-ai-950" : "border-border text-foreground",
              )}
            >
              {step.label}
              {step.added ? <span className="text-[12px] font-medium text-ai-700">New step</span> : null}
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>

      <div className="mt-4 flex min-h-[22px] flex-wrap gap-x-5 gap-y-1 text-[13px] font-medium text-shopify-700">
        {stage >= 2 ? (
          <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-1.5">
            <Check size={15} aria-hidden /> Replayed on past conversations
          </motion.span>
        ) : null}
        {stage >= 3 ? (
          <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-1.5">
            <Check size={15} aria-hidden /> Published as a new version
          </motion.span>
        ) : null}
      </div>
    </div>
  );
}

const CHAPTERS: { name: string; title: string; text: string; points: string[]; visual: () => ReactNode }[] = [
  {
    name: "Handle",
    title: "One inbox, with the work already done",
    text: "Every channel lands in one inbox. By the time you open a conversation, Tajeran has found the order, read the policy, and either answered or prepared the next step.",
    points: [
      "Refunds and cancellations wait in Approvals with the order, the policy, and the amount",
      "A handed-over conversation arrives with a summary, so nobody investigates twice",
      "Tajeran remembers the earlier messages in a conversation",
    ],
    visual: ApprovalVisual,
  },
  {
    name: "Supervise",
    title: "See what is happening right now",
    text: "Live shows who is waiting for a person, what is waiting for approval, and which automations are running. Desk shows how the whole operation is doing.",
    points: [
      "Time to first reply, time to resolve, and backlog age",
      "Top topics and tickets by channel",
      "How customers rated the automated answers, with the lowest-rated chats one click away",
    ],
    visual: SuperviseVisual,
  },
  {
    name: "Improve",
    title: "Change how it works by describing it",
    text: "Write the change in plain words. Tajeran proposes the edit to the workflow and replays it on past conversations, so you see what would have been sent before anything goes live.",
    points: [
      "Nothing changes for customers until you publish",
      "Every version is kept, and you can go back to an earlier one",
      "Answers come from your own help articles and policies",
    ],
    visual: ImproveVisual,
  },
];

function Chapter({ index, onActive }: { index: number; onActive: (index: number) => void }) {
  const chapter = CHAPTERS[index];
  const Visual = chapter.visual;
  const ref = useRef<HTMLDivElement>(null);
  const centered = useInView(ref, { margin: "-50% 0px -50% 0px" });

  useEffect(() => {
    if (centered) onActive(index);
  }, [centered, index, onActive]);

  return (
    <div ref={ref} className="flex flex-col justify-center py-12 lg:min-h-[80vh] lg:py-0">
      <p className="text-[14px] font-semibold text-primary">{chapter.name}</p>
      <h3 className="mt-2 font-[family-name:var(--font-display)] text-[28px] font-semibold leading-tight tracking-tight text-foreground sm:text-[34px]">
        {chapter.title}
      </h3>
      <p className="mt-4 max-w-lg text-[16px] leading-7 text-text-secondary">{chapter.text}</p>
      <ul className="mt-5 max-w-lg space-y-2.5">
        {chapter.points.map((point) => (
          <li key={point} className="flex gap-2.5 text-[14.5px] leading-6 text-foreground">
            <Check size={16} className="mt-1 shrink-0 text-primary" aria-hidden />
            {point}
          </li>
        ))}
      </ul>
      <div className="mt-8 lg:hidden">
        <Visual />
      </div>
    </div>
  );
}

// Three chapters named after the app's own sections. On wide screens the
// visual stays pinned while the text scrolls past it.
export function ProductTour() {
  const [active, setActive] = useState(0);
  const Visual = CHAPTERS[active].visual;

  return (
    <div className="lg:grid lg:grid-cols-2 lg:gap-16">
      <div>
        {CHAPTERS.map((chapter, index) => (
          <Chapter key={chapter.name} index={index} onActive={setActive} />
        ))}
      </div>
      <div className="hidden lg:block">
        <div className="sticky top-0 flex h-screen items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              className="flex w-full justify-center"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: EASE }}
            >
              <Visual />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
