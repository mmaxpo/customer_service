"use client";

import Link from "next/link";
import { useRef } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";
import { Check } from "lucide-react";

import { cn } from "@/platform/utils";

import { Counter } from "./ProductTour";

const EASE = [0.22, 1, 0.36, 1] as const;

type Plan = { name: string; price: number | null; description: string; points: string[]; cta: string; href: string };

const PLANS: Plan[] = [
  {
    name: "Starter",
    price: 49,
    description: "For a small support team getting started.",
    points: ["Every channel in one inbox", "Agents answer order and shipping questions", "Approvals for refunds and cancellations"],
    cta: "Choose Starter",
    href: "/signup",
  },
  {
    name: "Growth",
    price: 149,
    description: "For stores ready to automate more conversations.",
    points: ["Everything in Starter", "Change workflows by describing them", "Replay changes on past conversations"],
    cta: "Choose Growth",
    href: "/signup",
  },
  {
    name: "Pro",
    price: 399,
    description: "For teams running support as an operation.",
    points: ["Everything in Growth", "Routing and teams", "Live view and Desk reports"],
    cta: "Choose Pro",
    href: "/signup",
  },
  {
    name: "Enterprise",
    price: null,
    description: "For larger brands with several stores or special requirements.",
    points: ["Everything in Pro", "Help setting up your workflows", "Terms that fit your company"],
    cta: "Contact us",
    href: "/contact",
  },
];

export function Pricing() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLUListElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.25 });

  return (
    <ul ref={ref} className="grid overflow-hidden rounded-xl border border-border bg-surface sm:grid-cols-2 lg:grid-cols-4">
      {PLANS.map((plan, index) => (
        <motion.li
          key={plan.name}
          initial={reduced ? false : { opacity: 0, y: 28 }}
          animate={inView || reduced ? { opacity: 1, y: 0 } : undefined}
          transition={{ duration: 0.6, ease: EASE, delay: index * 0.09 }}
          className={cn(
            "flex flex-col border-border p-6 sm:p-7",
            index > 0 && "border-t sm:border-t-0",
            index % 2 === 1 && "sm:border-l",
            index >= 2 && "sm:border-t lg:border-t-0",
            index === 2 && "lg:border-l",
          )}
        >
          <h3 className="text-[15px] font-semibold text-foreground">{plan.name}</h3>
          <p className="mt-3 flex items-baseline gap-1.5 font-[family-name:var(--font-display)] text-[44px] font-semibold leading-none tracking-tight text-foreground">
            {plan.price === null ? (
              "Custom"
            ) : (
              <>
                <span>
                  $<span className="tabular-nums"><Counter to={plan.price} play={inView} /></span>
                </span>
                <span className="font-sans text-[14px] font-normal tracking-normal text-text-secondary">per month</span>
              </>
            )}
          </p>
          <p className="mt-3 min-h-[48px] text-[14.5px] leading-6 text-text-secondary">{plan.description}</p>
          <ul className="mt-5 flex-1 space-y-2.5">
            {plan.points.map((point) => (
              <li key={point} className="flex gap-2.5 text-[14px] leading-6 text-foreground">
                <Check size={16} className="mt-1 shrink-0 text-primary" aria-hidden />
                {point}
              </li>
            ))}
          </ul>
          <Link
            href={plan.href}
            className={cn(
              "mt-7 inline-flex h-11 items-center justify-center rounded-control text-[14px] font-semibold transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2",
              plan.price === null
                ? "border border-border text-foreground hover:bg-muted"
                : "bg-primary text-primary-foreground hover:bg-primary-hover",
            )}
          >
            {plan.cta}
          </Link>
        </motion.li>
      ))}
    </ul>
  );
}
