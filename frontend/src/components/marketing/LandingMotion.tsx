"use client";

import { useRef } from "react";
import { motion, useReducedMotion, useScroll } from "motion/react";

import { cn } from "@/platform/utils";

const EASE = [0.22, 1, 0.36, 1] as const;

// The headline rises word by word out of a mask, once, on page load.
export function HeroHeadline({ text, className }: { text: string; className?: string }) {
  const reduced = useReducedMotion();
  return (
    <h1 className={className} aria-label={text}>
      {text.split(" ").map((word, index) => (
        <span key={index} aria-hidden className="inline-block overflow-hidden pb-[0.12em] align-bottom">
          <motion.span
            className="inline-block"
            initial={reduced ? false : { y: "110%" }}
            animate={{ y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.1 + index * 0.05 }}
          >
            {word}&nbsp;
          </motion.span>
        </span>
      ))}
    </h1>
  );
}

// Setup is a real sequence, so it is numbered; the line draws as you scroll.
export function SetupSteps({ steps }: { steps: { title: string; text: string }[] }) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLOListElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.8", "end 0.6"] });

  return (
    <ol ref={ref} className="relative grid gap-8 md:grid-cols-4 md:gap-6">
      <span aria-hidden className="absolute left-0 right-0 top-[15px] hidden h-px bg-border md:block" />
      <motion.span
        aria-hidden
        className="absolute left-0 right-0 top-[15px] hidden h-px origin-left bg-foreground md:block"
        style={{ scaleX: reduced ? 1 : scrollYProgress }}
      />
      {steps.map((step, index) => (
        <li key={step.title} className="relative">
          <span
            className={cn(
              "relative flex h-[30px] w-[30px] items-center justify-center rounded-full bg-foreground",
              "text-[13px] font-semibold tabular-nums text-white ring-8 ring-surface",
            )}
          >
            {index + 1}
          </span>
          <h3 className="mt-4 text-[16px] font-semibold text-foreground">{step.title}</h3>
          <p className="mt-2 text-[14.5px] leading-6 text-text-secondary">{step.text}</p>
        </li>
      ))}
    </ol>
  );
}
