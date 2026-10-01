"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Settings } from "lucide-react";

import { authApi } from "@/platform/api";
import { TajeranMark } from "@/ui/brand/TajeranMark";

import { configurationNav, isActivePath, primaryNav } from "./navigation";

function currentLabel(pathname: string) {
  const items = [...primaryNav.flatMap((group) => group.items), ...configurationNav];
  return items.find((item) => isActivePath(pathname, item.href))?.label ?? "Tajeran";
}

export default function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="flex h-12 shrink-0 items-center gap-2.5 border-b border-border bg-surface px-4 lg:hidden">
      <Link href="/app/inbox" className="rounded-control focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
        <TajeranMark size={26} title="Tajeran" />
      </Link>
      <span className="flex-1 text-sm font-semibold text-foreground">{currentLabel(pathname)}</span>
      {/* The rail is hidden at this width, so settings and log out live here. */}
      <Link
        href="/app/settings"
        aria-label="Settings"
        className="flex h-9 w-9 items-center justify-center rounded-control text-text-secondary hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <Settings size={18} strokeWidth={1.75} aria-hidden />
      </Link>
      <button
        type="button"
        onClick={() => void authApi.logout()}
        aria-label="Log out"
        className="flex h-9 w-9 items-center justify-center rounded-control text-text-secondary hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <LogOut size={18} strokeWidth={1.75} aria-hidden />
      </button>
    </header>
  );
}
