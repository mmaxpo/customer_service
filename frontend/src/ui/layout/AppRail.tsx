"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

import { useApprovals } from "@/domains/customer-service/inbox/features/approvals/hooks";
import { useWaitingForPerson } from "@/domains/customer-service/live/useWaitingForPerson";
import { authApi } from "@/platform/api";
import { TajeranMark } from "@/ui/brand/TajeranMark";
import { cn } from "@/platform/utils";

import { configurationNav, isActivePath, primaryNav, type NavItem } from "./navigation";

function RailLink({ item, count, compact = false }: { item: NavItem; count?: number; compact?: boolean }) {
  const pathname = usePathname();
  const active = isActivePath(pathname, item.href);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      title={item.label}
      className={cn(
        "group relative flex w-full flex-col items-center gap-1 rounded-control px-1 py-2 text-center transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
        active
          ? "bg-primary/[0.08] text-primary"
          : "text-text-secondary hover:bg-muted hover:text-foreground",
      )}
    >
      <span className="relative">
        <Icon size={compact ? 16 : 18} strokeWidth={1.75} aria-hidden />
        {count ? (
          <span className="absolute -right-2.5 -top-1.5 min-w-4 rounded-full bg-warning px-1 text-[10px] font-semibold leading-4 text-white tabular-nums">
            {count > 99 ? "99+" : count}
            <span className="sr-only"> waiting</span>
          </span>
        ) : null}
      </span>
      <span className={cn("leading-tight", compact ? "text-[10px]" : "text-[10.5px] font-medium")}>
        {item.label}
      </span>
    </Link>
  );
}

export default function AppRail() {
  const { waits } = useApprovals();
  const waiting = useWaitingForPerson();

  return (
    <nav
      aria-label="Main"
      className="sticky top-0 hidden h-dvh w-[76px] shrink-0 flex-col items-center border-r border-border bg-surface px-2 py-3 lg:flex"
    >
      <Link
        href="/app/inbox"
        className="mb-3 rounded-control focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <TajeranMark size={30} title="Tajeran" />
      </Link>

      <div className="flex w-full flex-1 flex-col gap-3 overflow-y-auto">
        {primaryNav.map((group, index) => (
          <section key={group.label} aria-labelledby={`nav-${group.label}`} className="flex flex-col gap-0.5">
            {index > 0 ? <div className="mx-2 mb-2 border-t border-border" aria-hidden /> : null}
            <h2 id={`nav-${group.label}`} className="sr-only">{group.label}</h2>
            {group.items.map((item) => (
              <RailLink
                key={item.href}
                item={item}
                count={item.badge === "approvals" ? waits.length : item.badge === "waiting" ? waiting?.length : undefined}
              />
            ))}
          </section>
        ))}
      </div>

      <section aria-label="Configuration" className="mt-3 flex w-full flex-col gap-0.5 border-t border-border pt-3">
        {configurationNav.map((item) => (
          <RailLink key={item.href} item={item} compact />
        ))}
        <button
          type="button"
          onClick={() => void authApi.logout()}
          title="Log out"
          className="flex w-full flex-col items-center gap-1 rounded-control px-1 py-2 text-text-secondary transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <LogOut size={16} strokeWidth={1.75} aria-hidden />
          <span className="text-[10px] leading-tight">Log out</span>
        </button>
      </section>
    </nav>
  );
}
