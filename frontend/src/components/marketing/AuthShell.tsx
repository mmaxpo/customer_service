"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";

import { AGENTS } from "./AgentsScene";
import { aura, display, palette } from "./brand";

const EASE = [0.22, 1, 0.36, 1] as const;

export const authInput =
  "mt-1.5 h-11 w-full rounded-control border border-border bg-surface px-3 text-[14.5px] text-foreground outline-none transition-shadow placeholder:text-text-secondary/60 focus:border-primary focus:ring-2 focus:ring-primary/20";
export const authLabel = "block text-[13.5px] font-medium text-foreground";
export const authButton =
  "h-11 w-full rounded-control bg-primary px-4 text-[14.5px] font-semibold text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 disabled:opacity-60";

// A status or error line that slides in under the form.
export function AuthStatus({ message, tone = "info" }: { message: string | null; tone?: "info" | "error" }) {
  return (
    <AnimatePresence initial={false}>
      {message ? (
        <motion.p
          key={message}
          role={tone === "error" ? "alert" : "status"}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className={cn(
            "mt-4 rounded-control px-3 py-2 text-[13.5px]",
            tone === "error" ? "bg-danger/10 text-danger" : "bg-muted text-text-secondary",
          )}
        >
          {message}
        </motion.p>
      ) : null}
    </AnimatePresence>
  );
}

const STEP_MS = 1300;
const HOLD_MS = 2600;

// The agents taking their turns, on a loop, beside the form.
function AgentRelay() {
  const reduced = useReducedMotion();
  const [played, setPlayed] = useState(0);
  const count = reduced ? AGENTS.length : played;

  useEffect(() => {
    if (reduced) return;
    const timer = window.setTimeout(
      () => setPlayed(played === AGENTS.length ? 0 : played + 1),
      played === AGENTS.length ? HOLD_MS : STEP_MS,
    );
    return () => window.clearTimeout(timer);
  }, [played, reduced]);

  return (
    <ol className="w-full max-w-sm rounded-xl border border-border bg-surface p-5 shadow-elevated">
      {AGENTS.map((agent, index) => {
        const reached = count > index;
        const Icon = agent.icon;
        return (
          <li key={agent.name} className={cn("flex items-center gap-3 py-2.5", index > 0 && "border-t border-border")}>
            <motion.span
              animate={{ scale: count === index + 1 ? 1.12 : 1 }}
              transition={{ duration: 0.3, ease: EASE }}
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-colors duration-300",
                reached ? "border-transparent text-white" : "border-border bg-surface text-text-secondary",
              )}
              style={reached ? { backgroundColor: agent.color } : undefined}
            >
              <Icon size={16} aria-hidden />
            </motion.span>
            <span className="min-w-0">
              <span className={cn("block text-[13.5px] font-medium transition-colors duration-300", reached ? "text-foreground" : "text-text-secondary")}>
                {agent.name}
              </span>
              <span className={cn("block truncate text-[12.5px] text-text-secondary transition-opacity duration-300", reached ? "opacity-100" : "opacity-0")}>
                {agent.finding}
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

type Props = { title: string; subtitle: string; children: ReactNode; footer: ReactNode };

export function AuthShell({ title, subtitle, children, footer }: Props) {
  const reduced = useReducedMotion();
  return (
    <main className={cn(display.variable, "grid min-h-screen bg-surface text-foreground lg:grid-cols-2")} style={palette}>
      <div className="flex flex-col px-5 py-6 sm:px-10">
        <Link
          href="/"
          className="flex w-fit items-center gap-2 rounded-control text-[15px] font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2"
        >
          <TajeranMark size={26} />
          Tajeran.ai
        </Link>

        <motion.div
          className="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center py-10"
          initial={reduced ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          <h1 className="font-[family-name:var(--font-display)] text-[34px] font-semibold leading-[1.1] tracking-tight">{title}</h1>
          <p className="mt-2.5 text-[15px] leading-6 text-text-secondary">{subtitle}</p>
          {children}
          <div className="mt-6 space-y-2 text-[13.5px] text-text-secondary">{footer}</div>
        </motion.div>
      </div>

      <div className="relative isolate hidden items-center justify-center overflow-hidden border-l border-border bg-background p-10 lg:flex">
        <div aria-hidden className="pointer-events-none absolute inset-x-10 top-1/4 -z-10 h-1/2 opacity-30 blur-3xl" style={aura} />
        <div className="w-full max-w-sm">
          <p className="mb-5 font-[family-name:var(--font-display)] text-[26px] font-semibold leading-tight tracking-tight">
            Your agents pick up the next conversation as soon as you are in.
          </p>
          <AgentRelay />
        </div>
      </div>
    </main>
  );
}
