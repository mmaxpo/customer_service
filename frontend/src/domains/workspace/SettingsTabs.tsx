"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/platform/utils";

import { ThemeSwitch } from "./ThemeSwitch";

const tabs = [
  { href: "/app/settings", label: "Workspace" },
  { href: "/app/settings/team", label: "Team" },
  { href: "/app/settings/connections", label: "Connections" },
  { href: "/app/settings/chat-widget", label: "Chat widget" },
];

export function SettingsTabs() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings" className="mt-5 flex items-end gap-4 border-b border-border sm:gap-5">
      {tabs.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px whitespace-nowrap border-b-2 pb-2 text-[13.5px] font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
              active ? "border-primary text-foreground" : "border-transparent text-text-secondary hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
      <ThemeSwitch />
    </nav>
  );
}
