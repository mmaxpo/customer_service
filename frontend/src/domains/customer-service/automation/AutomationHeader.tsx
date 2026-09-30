"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/platform/utils";

const sections = [
  { href: "/app/workflows", label: "Workflows" },
  { href: "/app/workflows/review", label: "Needs review" },
];

export function AutomationHeader({
  title,
  description,
  reviewCount,
  actions,
}: {
  title: string;
  description: string;
  reviewCount?: number;
  actions?: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <header className="mb-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[18px] font-semibold text-foreground">{title}</h1>
          <p className="mt-0.5 text-[13.5px] text-text-secondary">{description}</p>
        </div>
        {actions}
      </div>
      <nav aria-label="Automation" className="mt-4 flex gap-5 border-b border-border">
        {sections.map((section) => {
          const active = pathname === section.href;
          return (
            <Link
              key={section.href}
              href={section.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "-mb-px flex items-center gap-1.5 border-b-2 pb-2 text-[13.5px] font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                active ? "border-primary text-foreground" : "border-transparent text-text-secondary hover:text-foreground",
              )}
            >
              {section.label}
              {section.href.endsWith("review") && reviewCount ? (
                <span className="rounded-full bg-warning/10 px-1.5 text-[11px] font-semibold tabular-nums text-warning">
                  {reviewCount}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
