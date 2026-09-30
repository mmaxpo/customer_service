"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/platform/utils";

const tabs = [
  { href: "/app/live", label: "Now" },
  { href: "/app/live/activity", label: "Activity log" },
];

export function LiveHeader({ description }: { description: string }) {
  const pathname = usePathname();

  return (
    <header className="mb-5">
      <h1 className="text-[18px] font-semibold text-foreground">Live</h1>
      <p className="mt-0.5 text-[13.5px] text-text-secondary">{description}</p>
      <nav aria-label="Live" className="mt-4 flex gap-5 border-b border-border">
        {tabs.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "-mb-px border-b-2 pb-2 text-[13.5px] font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                active ? "border-primary text-foreground" : "border-transparent text-text-secondary hover:text-foreground",
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
