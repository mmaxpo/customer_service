"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
      <span className="text-sm font-semibold text-foreground">{currentLabel(pathname)}</span>
    </header>
  );
}
